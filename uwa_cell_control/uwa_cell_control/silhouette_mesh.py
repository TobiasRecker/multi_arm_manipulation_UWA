"""CPU visual-hull candidate from reviewed image-bound silhouettes. Offline only.

This estimates an outer envelope, not hidden surfaces or material occupancy.
Original optics and quality exclusions are immutable inputs. Validation views
never carve the volume or select texture cameras.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import cv2
import numpy as np
from scipy import ndimage


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project(points, camera, width):
    """Native distorted OpenCV projection; pixel-center-correct proxy scaling."""
    points = np.asarray(points, float)
    T = np.asarray(camera['T_camera_board'], float)
    q = points @ T[:3, :3].T + T[:3, 3]
    pixels = np.empty((len(points), 2))
    # Bound OpenCV's returned Jacobian memory, including rational14 optics.
    for start in range(0, len(points), 20000):
        end = min(start+20000, len(points))
        p, _ = cv2.projectPoints(q[start:end], np.zeros(3), np.zeros(3),
            np.asarray(camera['K'], float), np.asarray(camera['D'], float))
        pixels[start:end] = (p.reshape(-1, 2)+.5)*(width/camera['image_size'][0])-.5
    return pixels, q[:, 2]


def mask_from_annotation(item, width, height):
    def polygon(points):
        p = np.asarray(points, float)
        if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or not np.isfinite(p).all():
            raise ValueError('Mask requires finite 2D polygon vertices')
        if np.any(p < 0) or np.any(p >= [width, height]):
            raise ValueError('Mask polygon leaves its source image')
        if item['rotate_180']: p = np.array([width-1, height-1])-p
        return np.rint(p).astype(np.int32)
    mask = np.zeros((height, width), np.uint8)
    cv2.fillPoly(mask, [polygon(item['outer_polygon'])], 1)
    for hole in item.get('holes', []): cv2.fillPoly(mask, [polygon(hole)], 0)
    if not mask.any(): raise ValueError('Empty silhouette')
    return mask.astype(bool)


def pixel_membership(points, camera, mask, tolerance=0.):
    p, depth = project(points, camera, mask.shape[1])
    good = (depth > 0) & np.isfinite(p).all(1)
    good &= (p[:, 0] >= 0) & (p[:, 0] < mask.shape[1]) & (p[:, 1] >= 0) & (p[:, 1] < mask.shape[0])
    xy = np.clip(np.rint(p).astype(np.int64), [0, 0], [mask.shape[1]-1, mask.shape[0]-1])
    expanded = ndimage.distance_transform_edt(~mask) <= tolerance if tolerance else mask
    return good & expanded[xy[:, 1], xy[:, 0]]


def voxel_surface(occupied, lower, pitch):
    """Exposed cube faces, outward winding; no smoothing that changes evidence."""
    vertices, faces = [], []
    # In-plane axes cycle with a positive cross product toward the normal axis.
    for axis in range(3):
        u, v = (axis+1) % 3, (axis+2) % 3
        for sign in (-1, 1):
            neighbor = np.roll(occupied, -sign, axis=axis)
            boundary = [slice(None)]*3;boundary[axis] = -1 if sign > 0 else 0
            neighbor[tuple(boundary)] = False
            cells = np.argwhere(occupied & ~neighbor)
            if not len(cells): continue
            corner = cells.copy()
            if sign > 0: corner[:, axis] += 1
            quad = np.repeat(corner[:, None, :], 4, axis=1)
            quad[:, 1, u] += 1;quad[:, 2, u] += 1;quad[:, 2, v] += 1;quad[:, 3, v] += 1
            if sign < 0: quad = quad[:, [0, 3, 2, 1]]
            offset = sum(len(x) for x in vertices)
            vertices.append(quad.reshape(-1, 3))
            index = np.arange(len(cells)*4).reshape(-1, 4)+offset
            faces.extend([index[:, [0, 1, 2]], index[:, [0, 2, 3]]])
    if not vertices: raise ValueError('Empty visual hull; inspect masks/poses rather than relaxing gates')
    raw = np.concatenate(vertices)
    unique, inverse = np.unique(raw, axis=0, return_inverse=True)
    return np.asarray(lower)+unique*pitch, inverse[np.concatenate(faces)]


def tetra_surface(occupied, lower, pitch):
    """Consistent 6-tetrahedron, 0.5 isosurface of padded binary cell centres.

    This avoids nonmanifold edge-only contacts of exposed voxel cubes. It is
    deterministic linear interpolation, not measured sub-voxel geometry.
    """
    nodes=np.pad(occupied.astype(np.uint8),1)
    offsets=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
    shape=np.array(nodes.shape)-1
    values=np.stack([nodes[x:x+shape[0],y:y+shape[1],z:z+shape[2]] for x,y,z in offsets],axis=-1)
    boundary=(values.sum(-1)>0)&(values.sum(-1)<8)
    origins=np.argwhere(boundary);states=values[boundary]
    triangles=[]
    for tet in ([0,1,2,6],[0,2,3,6],[0,3,7,6],[0,7,4,6],[0,4,5,6],[0,5,1,6]):
        local=offsets[tet];codes=states[:,tet]@np.array([1,2,4,8])
        for code in range(1,15):
            base=origins[codes==code]
            if not len(base):continue
            high=[i for i in range(4) if code&(1<<i)];low=[i for i in range(4) if not code&(1<<i)]
            if len(high)==1:edges=[(high[0],j) for j in low];faces=[[0,1,2]]
            elif len(low)==1:edges=[(low[0],j) for j in high];faces=[[0,1,2]]
            else:
                a,b=high;c,d=low;edges=[(a,c),(a,d),(b,d),(b,c)];faces=[[0,1,2],[0,2,3]]
            doubled=np.array([local[a]+local[b] for a,b in edges])
            outward=local[low].mean(0)-local[high].mean(0)
            for face in faces:
                tri=doubled[face]
                if np.cross(tri[1]-tri[0],tri[2]-tri[0])@outward<0:tri=tri[[0,2,1]]
                triangles.append((2*base[:,None,:]+tri).reshape(-1,3))
    if not triangles:raise ValueError('Empty isosurface')
    raw=np.concatenate(triangles);unique,inverse=np.unique(raw,axis=0,return_inverse=True)
    return np.asarray(lower)+(unique*.5-.5)*pitch,inverse.reshape(-1,3)


def silhouette_projection(points, camera, shape, pitch):
    pixels, z = project(points, camera, shape[1])
    image = np.zeros(shape, np.uint8)
    keep = (z > 0) & np.isfinite(pixels).all(1)
    xy = np.rint(pixels[keep]).astype(np.int64)
    xy = xy[(xy[:, 0]>=0)&(xy[:, 0]<shape[1])&(xy[:, 1]>=0)&(xy[:, 1]<shape[0])]
    image[xy[:, 1], xy[:, 0]] = 1
    # Conservative cell footprint, clearly recorded; not a subpixel surface fit.
    radius = max(1, int(np.ceil(pitch*camera['K'][0][0]*shape[1]/camera['image_size'][0]/np.median(z[keep]))))
    return cv2.dilate(image, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*radius+1, 2*radius+1))).astype(bool)


def reconstruct(models_path, annotations_path, output):
    started = time.monotonic()
    models_path, annotations_path, output = map(Path, (models_path, annotations_path, output))
    cameras = json.loads(models_path.read_text());spec = json.loads(annotations_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    width = spec['proxy_width'];pitch = float(spec['voxel_size_m']);tol = float(spec['mask_tolerance_px'])
    bounds = np.asarray(spec['bounds_board_m'], float)
    if bounds.shape != (2, 3) or not np.isfinite(bounds).all() or np.any(bounds[1] <= bounds[0]):
        raise ValueError('Invalid metric search bounds')
    if not 0.001 <= pitch <= .02 or not 0 <= tol <= 5: raise ValueError('Invalid declared discretization/tolerance')
    shape = np.ceil((bounds[1]-bounds[0])/pitch).astype(int)
    support = spec.get('support_plane_board_z_m')
    if support is not None and (not np.isfinite(support) or abs(float(support)-bounds[1, 2])>1e-9
            or abs(bounds[0, 2]+shape[2]*pitch-float(support))>1e-8):
        raise ValueError('Explicit support plane must match the aligned upper Z grid boundary')
    if np.prod(shape) > 10000000: raise ValueError('Grid exceeds CPU memory budget')
    masks = {}
    for name, item in spec['views'].items():
        if name not in cameras: raise ValueError('Unknown camera view')
        c = cameras[name]
        if not c['metric_eligible']: raise ValueError('Metric-excluded view cannot contribute: '+name)
        if item['image_sha256'] != c['image_sha256'] or sha(c['image']) != c['image_sha256']:
            raise ValueError('Mask/image binding changed')
        if item['role'] not in ('fit', 'validation'): raise ValueError('Assign fit/validation before reconstruction')
        height = round(c['image_size'][1]*width/c['image_size'][0])
        masks[name] = mask_from_annotation(item, width, height)
        cv2.imwrite(str(output/(name+'_mask.png')), masks[name].astype(np.uint8)*255)
        raw = cv2.imread(c['image']);small = cv2.resize(raw, (width, height))
        cv2.imwrite(str(output/(name+'_photo.jpg')), small)
        overlay = small.copy();overlay[masks[name]] = (.6*overlay[masks[name]]+.4*np.array([30,210,30])).astype(np.uint8)
        cv2.imwrite(str(output/(name+'_mask_review.jpg')), overlay)
    fit = [k for k, v in spec['views'].items() if v['role']=='fit']
    validation = [k for k, v in spec['views'].items() if v['role']=='validation']
    if len(fit)<3 or not validation: raise ValueError('At least three fit views and independent validation required')
    indices = np.arange(int(np.prod(shape)))
    for name in fit:
        cells = np.array(np.unravel_index(indices, tuple(shape))).T
        points = bounds[0]+(cells+.5)*pitch
        indices = indices[pixel_membership(points, cameras[name], masks[name], tol)]
        print(json.dumps(dict(carved_by=name, occupied_voxels=len(indices))), flush=True)
        if not len(indices): raise ValueError('Inconsistent input silhouettes/poses; no hull')
    occupied = np.zeros(tuple(shape), bool);occupied.ravel()[indices] = True
    cells = np.argwhere(occupied)
    np.savez_compressed(output/'occupied_grid.npz',occupied=occupied,lower=bounds[0],pitch=pitch)
    (output/'grid_bounds.json').write_text(json.dumps(dict(search_bounds=bounds.tolist(),
        occupied_min_cell=cells.min(0).tolist(),occupied_max_cell=cells.max(0).tolist(),
        shape=shape.tolist(),lower_touched=(cells.min(0)==0).tolist(),upper_touched=(cells.max(0)==shape-1).tolist()),indent=2)+'\n')
    upper_touch = cells.max(0)==shape-1
    if support is not None: upper_touch[2] = False  # A declared physical support constraint, not a free search bound.
    if np.any(cells.min(0)==0) or np.any(upper_touch):
        raise ValueError('Hull touches search bounds; enlarge explicit bounds before estimating dimensions')
    surface_method=spec.get('surface_method','exposed_voxels')
    if surface_method not in ('exposed_voxels','tetrahedral_isosurface'):raise ValueError('Unknown surface method')
    vertices, faces = (tetra_surface if surface_method=='tetrahedral_isosurface' else voxel_surface)(occupied, bounds[0], pitch)
    np.savez_compressed(output/'mesh_board.npz', vertices=vertices, faces=faces)
    surface = bounds[0]+(np.argwhere(occupied & ~ndimage.binary_erosion(occupied))+.5)*pitch
    validation_result = {}
    for name in [*fit, *validation]:
        mask = masks[name]
        rendered = silhouette_projection(surface, cameras[name], mask.shape, pitch)
        iou = float((mask & rendered).sum()/max(1, (mask | rendered).sum()))
        validation_result[name] = dict(role=spec['views'][name]['role'], silhouette_iou=iou)
        raw = cv2.imread(str(output/(name+'_photo.jpg')))
        raw[rendered] = (.5*raw[rendered]+.5*np.array([0,90,255])).astype(np.uint8)
        cv2.imwrite(str(output/(name+'_projection_review.jpg')), raw)
    result = dict(schema=1, method='voxel_visual_hull', candidate_only=True,
        source_models=str(models_path.resolve()),source_models_sha256=sha(models_path),
        source_annotations=str(annotations_path.resolve()),source_annotations_sha256=sha(annotations_path),
        voxel_size_m=pitch,mask_tolerance_proxy_px=tol,proxy_width=width,
        support_plane_board_z_m=support,
        surface_method=surface_method,
        bounds_board_m=bounds.tolist(),mesh_bounds_board_m=[vertices.min(0).tolist(),vertices.max(0).tolist()],
        dimensions_axis_aligned_board_m=np.ptp(vertices, axis=0).tolist(),
        occupied_voxels=len(indices),vertices=len(vertices),triangles=len(faces),
        fit_views=fit,validation_views=validation,projection_checks=validation_result,
        original_failed_calibration_views=[k for k in fit if cameras[k]['calibration_passed'] is False],
        geometry_validated=False,tracking_validated=False,manipulation_approved=False,
        limitations=['Outer envelope only; cage openings and hidden concavities not reconstructed.',
            'Manually traced masks; selected two-pixel tolerance is not measured physical uncertainty.',
            'Board-based poses and original optics fixed; no nominal robot or object pose prior.',
            'Voxel pitch is discretization, not proven accuracy; no independent physical metrology.',
            'Projection IoU uses a conservative one-cell image footprint, not exact surface rasterization.'],
        duration_s=time.monotonic()-started)
    (output/'reconstruction.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(output=str(output),dimensions_m=result['dimensions_axis_aligned_board_m'],triangles=len(faces))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--models',type=Path,required=True)
    p.add_argument('--annotations',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();cv2.setNumThreads(2);reconstruct(a.models,a.annotations,a.output)
