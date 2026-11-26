"""Finite RGB-D geometry evidence alongside the native-image carton pose.

Use the actual rectified RGB/depth projection, never index depth with 8K
pixels. Raw depth is retained; no historical/global depth offset is applied.
"""
from pathlib import Path
import json
from datetime import datetime
import cv2
import numpy as np


def checked_path(directory, name):
    path = (directory/name).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError('RGB-D input path is not a file inside its capture')
    return path


def projected_polygon(points, T, K):
    pixels = cv2.projectPoints(np.asarray(points,float),cv2.Rodrigues(T[:3,:3])[0],T[:3,3],K,np.zeros(5))[0].reshape(-1,2)
    return np.rint(pixels).astype(np.int32)


def table_heights(depth, mask, K, Ttc):
    y,x=np.nonzero(mask & (depth>0))
    if len(x)<30:
        raise ValueError('Too few valid depth samples in the selected surface')
    z=depth[y,x].astype(float)/1000
    camera=np.column_stack(((x-K[0,2])/K[0,0]*z,(y-K[1,2])/K[1,1]*z,z))
    return (camera @ Ttc[:3,:3].T + Ttc[:3,3])[:,2]


def camera_points(depth, mask, K):
    y,x=np.nonzero(mask & (depth>0))
    if len(x)<30:
        raise ValueError('Too few valid depth samples in the selected surface')
    z=depth[y,x].astype(float)/1000
    return np.column_stack(((x-K[0,2])/K[0,0]*z,(y-K[1,2])/K[1,1]*z,z))


def check_depth(directory, context, geometry, native_metadata, output=None):
    from register_carton_from_oak import right_board_observation, validate_visible_board_projection
    from object_scan_perception import support_plane
    directory=Path(directory)
    report=json.loads((directory/'metadata.json').read_text())
    projection=report['projection'];K=np.asarray(projection['K'],float)
    if (report.get('success') is not True or report.get('kind')!='rgbd'
            or report.get('device_id')!=context['device_id'] or report.get('requested_focus')!=context['focus']
            or K.shape!=(3,3) or not np.isfinite(K).all()
            or not np.array_equal(K,np.asarray(projection['depth_K'])) or np.any(projection['D'])
            or projection.get('coordinate_frame')!='CAM_A undistorted optical: X right, Y down, Z forward'):
        raise ValueError('RGB-D camera/focus/rectified projection does not match this measurement')
    size=tuple(projection['size']);Tct=np.asarray(context['T_camera_table']);Ttc=np.linalg.inv(Tct)
    Tco=Tct@np.asarray(geometry['T_table_object'])
    L,W=np.max(np.asarray(context['model_corners_m'])[:,:2],axis=0)
    # An interior patch avoids the mixed stereo pixels at cardboard edges.
    points=[[x,y,context['floor_z_m']] for x,y in [(.3*L,.3*W),(.7*L,.3*W),(.7*L,.7*W),(.3*L,.7*W)]]
    floor_polygon=projected_polygon(points,Tco,K)
    results=[];sources=[directory/'metadata.json']
    board_check=None
    for pair in report['pairs']:
        if pair['actual_focus']!=context['focus']:
            raise ValueError('RGB-D focus changed between frames')
        image_path=checked_path(directory,pair['rgb_path']);depth_path=checked_path(directory,pair['depth_path'])
        image=cv2.imread(str(image_path));depth=cv2.imread(str(depth_path),cv2.IMREAD_UNCHANGED)
        if image is None or depth is None or depth.dtype!=np.uint16 or tuple(depth.shape[::-1])!=size or tuple(image.shape[1::-1])!=size:
            raise ValueError('RGB and depth do not share their recorded projection grid')
        sources.extend([image_path,depth_path])
        obj,uv=right_board_observation(image)
        # Validate the existing camera pose on visible markers, do not re-fit it.
        try:
            board_check=dict(status='checked',**validate_visible_board_projection(obj,uv,np.asarray(context['T_camera_board']),K,np.zeros(5)))
        except ValueError as error:
            board_check=dict(status='unavailable',reason=str(error))
        # Independently measure table and inner floor in the SAME depth frame.
        # No board visibility or absolute depth bias correction is required for
        # this camera-local relative height. The native pose just selects ROIs.
        all_points=np.asarray(context['model_corners_m'])
        footprint=projected_polygon(all_points,Tco,K)
        low=footprint.min(0);high=footprint.max(0)
        table_mask=np.zeros(depth.shape,np.uint8)
        cv2.rectangle(table_mask,tuple(np.maximum(0,low-90)),tuple(np.minimum(np.array(size)-1,high+90)),255,-1)
        cv2.rectangle(table_mask,tuple(np.maximum(0,low-10)),tuple(np.minimum(np.array(size)-1,high+10)),0,-1)
        floor_mask=np.zeros(depth.shape,np.uint8);cv2.fillConvexPoly(floor_mask,floor_polygon,255)
        floor_mask=cv2.erode(floor_mask,np.ones((5,5),np.uint8))>0
        floor_count=int(np.count_nonzero(floor_mask & (depth>0)))
        table_count=int(np.count_nonzero((table_mask>0) & (depth>0)))
        if floor_count<30:
            raise ValueError(f'Inner floor patch has only {floor_count} valid depth pixels (30 needed); nearby table has {table_count}. Depth holes are not filled.')
        table=camera_points(depth,table_mask>0,K);floor=camera_points(depth,floor_mask,K)
        centre,normal,fraction,rms=support_plane(table)
        heights=(floor-centre)@normal
        results.append(dict(index=pair['index'],floor_above_local_table_mm=float(np.median(heights)*1000),
            floor_central_90_percent_mm=(np.percentile(heights,[5,95])*1000).tolist(),
            floor_valid_samples=len(floor),table_valid_samples=len(table),
            table_plane_inlier_fraction=fraction,table_plane_rms_mm=rms*1000))
        if pair['index']==0 and output is not None:
            marked=image.copy();cv2.polylines(marked,[floor_polygon],True,(0,0,0),5)
            cv2.polylines(marked,[floor_polygon],True,(255,255,255),2)
            cv2.imwrite(str(Path(output)/'depth-regions.jpg'),marked)
    native=json.loads(Path(native_metadata).read_text())
    gap=abs((datetime.fromisoformat(native['started_at'])-datetime.fromisoformat(report['started_at'])).total_seconds())
    return dict(status='measured' if gap<=60 else 'historical_comparison_only',
        native_to_depth_capture_gap_s=gap,depth_used_for_pose=False,
        camera_reference_check=board_check,per_frame=results,
        relative_floor_height_median_mm=float(np.median([r['floor_above_local_table_mm'] for r in results])),
        nominal_model_floor_height_mm=1000*context['floor_z_m'],floor_polygon_rgbd_xy=floor_polygon.tolist(),
        projection=projection,sources=[str(p.resolve()) for p in sources],
        absolute_accuracy_validated=False,
        interpretation='Camera-local floor/table height, selected by projected image ROIs. Board projection check is separate. No raw depth correction, pose averaging, or pixel-grid reuse.')
