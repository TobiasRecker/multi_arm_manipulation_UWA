#!/usr/bin/env python3
"""Generate the edge clamp, board holder and OAK 4 D tilt head in millimetres."""
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys

from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Compound

# Reuse the checked STEP/STL exporter and solid primitives of the left mount.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'oak_d_pro_left'))
from make_table_mount import box, combine, cylinder, export, prism

ROD_X = 30
BOARD_BACK_X = 61
BOARD_BOTTOM = 20
PULL_X = -18
PULL_ROWS = (-55, 55)
TOP_THICKNESS = 14
CLAMP_HEIGHT = 145
HEAD_PIVOT = 48
HEAD_OFFSET = 18
MOUNT_HOLE_Z = 17
CAMERA_MATE_X = 74
M12_PORT = (-18.9, -2.3)
BOTTOM_STEEL = 5
BOARD_LEVERAGE = 55
STRAP_HALF_WIDTH = 67


@dataclass(frozen=True)
class Dimensions:
    table: float
    setback: float
    rail: float
    bore: float
    board: float
    board_height: float
    rod_length: float
    tilt: float

    @property
    def rail_bottom(self):
        return -self.table-self.rail

    @property
    def board_top(self):
        return BOARD_BOTTOM+self.board_height


def horizontal(x, y, z, radius, span, direction):
    axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(*direction))
    return BRepPrimAPI_MakeCylinder(axis, radius, span).Shape()


def bore_y(x, z, radius, y=-40, span=80):
    return horizontal(x, y, z, radius, span, (0, 1, 0))


def bore_x(y, z, radius, x=0, span=100):
    return horizontal(x, y, z, radius, span, (1, 0, 0))


def socket(x, bottom, top, radius, bands, seat):
    sleeve = cylinder(x, 0, bottom, 17.5, top-bottom)
    ears = [box(x-24, -17, z-10, 17, 34, 20) for z in bands]
    cuts = [cylinder(x, 0, seat, radius, top-seat+1),
            box(x-26, -1.15, seat+.5, 26, 2.3, top-seat+1)]
    cuts.extend(bore_y(x-16.5, z, 2.75) for z in bands)
    return combine(combine(sleeve, ears), cuts, BRepAlgoAPI_Cut)


def guide(d, y):
    # Rear datum at x=61; front lip opens towards the printed face.
    front = BOARD_BACK_X+d.board+.6
    points = [(57, y-12, 12), (front+6, y-12, 12),
              (front+6, y-12, 34), (front+2.5, y-12, 34),
              (front, y-12, 28), (front, y-12, BOARD_BOTTOM),
              (BOARD_BACK_X, y-12, BOARD_BOTTOM), (BOARD_BACK_X, y-12, 30),
              (BOARD_BACK_X-2.2, y-12, 35), (57, y-12, 35)]
    return prism(points, (0, 24, 0))


def top_clamp(d):
    top = box(-33, -72, 0, 113, 144, TOP_THICKNESS)
    # An outside lip locates the 30 mm offset off the wooden edge.
    lip = box(-8, -69, -8, 8, 138, 9)
    sleeve = socket(ROD_X, 11, CLAMP_HEIGHT, d.bore/2, (29, 131), 11)
    ribs = []
    for sign in (-1, 1):
        ribs.append(prism([(33, sign*11, 13), (33, sign*61, 13),
                           (33, sign*12, 119)], (8, 0, 0)))
    centre_rib = prism([(37, -3, 13), (56, -3, 13), (39, -3, 113)], (0, 6, 0))
    upper = combine(top, [lip, sleeve, centre_rib, *ribs,
                          *(guide(d, y) for y in (-BOARD_LEVERAGE, BOARD_LEVERAGE))])
    cuts = [cylinder(PULL_X, y, -1, 4.5, TOP_THICKNESS+2) for y in PULL_ROWS]
    cuts += [cylinder(ROD_X, 0, 4, d.bore/2, CLAMP_HEIGHT-3),
             box(ROD_X-26, -1.15, 11.5, 26, 2.3, 5)]
    return combine(upper, cuts, BRepAlgoAPI_Cut)


def lower_clamp(d):
    rail_end = d.setback+d.rail
    z = d.rail_bottom
    jaw = box(-33, -72, z-25, rail_end+39, 144, 20)
    near = box(d.setback-4.5, -67, z-7, 4, 134, 12)
    far = box(rail_end+.5, -67, z-7, 4, 134, 12)
    jaw = combine(jaw, [near, far])
    return combine(jaw, [cylinder(PULL_X, y, z-26, 4.5, 22)
                         for y in PULL_ROWS], BRepAlgoAPI_Cut)


def edge_gauge(d):
    # Tip measures both the pull-side clearance and the profile outside face.
    z = d.rail_bottom
    profile = [(15, -8, 0), (15, -8, 4), (-21, -8, 4), (-21, -8, z-9),
               (d.setback+d.rail+1, -8, z-9),
               (d.setback+d.rail+1, -8, z-5), (d.setback-.5, -8, z-5),
               (d.setback-.5, -8, -d.table-2), (d.setback-4.5, -8, -d.table-2),
               (d.setback-4.5, -8, z-5), (-17, -8, z-5), (-17, -8, 0)]
    return prism(profile, (0, 16, 0))


def board_collar(d):
    z = d.board_top+7
    collar = combine(cylinder(ROD_X, 0, z-3, 18, 20),
                     [box(17, -22, z-3, 26, 44, 20)])
    inside_arm = box(39, -19, z-3, 17, 38, 18)
    finger = box(50, -5, z-22, BOARD_BACK_X-50, 10, 22)
    collar = combine(collar, [inside_arm, finger])
    fasteners = [bore_x(y, z+5, 2.75, 15, 30) for y in (-16, 16)]
    for y in (-9.5, 9.5):
        fasteners += [bore_x(y, z+5, 2.25, 44, 14),
                      box(46.5, y-3.6, z+1.1, 3.8, 7.2, 16)]
    common = combine(collar, [cylinder(ROD_X, 0, z-4, d.bore/2, 22),
                              box(29.5, -25, z-4, 1., 50, 24),
                              *fasteners], BRepAlgoAPI_Cut)
    inside = combine(common, [box(30.5, -24, z-23, 44, 48, 45)], BRepAlgoAPI_Common)
    outside = combine(common, [box(5, -24, z-23, 24.5, 48, 45)], BRepAlgoAPI_Common)
    return inside, outside


def board_slider(d):
    z = d.board_top
    front = BOARD_BACK_X+d.board+.8
    spine = box(56, -18, z-21, 4.5, 36, 44)
    roof = box(59, -18, z, front+5-59, 36, 5)
    lip = box(front, -18, z-9, 5, 36, 10)
    part = combine(spine, [roof, lip])
    cuts = []
    for y in (-9.5, 9.5):
        cuts.extend([bore_x(y,z-17,2.3,54,9), bore_x(y,z+12,2.3,54,9),
                     box(54,y-2.3,z-17,9,4.6,29)])
    return combine(part, cuts, BRepAlgoAPI_Cut)


def tilt_shoe(d):
    # The rod comes up to z=2. The Y-axis tilt pivot is at z=48.
    base = socket(0, -34, 10, d.bore/2, (-22,), -34)
    # Close the top of the bore to make a 36 mm insertion stop.
    base = combine(base, [cylinder(0, 0, 2, 13., 8)])
    forks = []
    for y in (-18, 9):
        forks.extend([box(HEAD_OFFSET-19, y, 7, 15, 9, HEAD_PIVOT-7),
                      bore_y(HEAD_OFFSET, HEAD_PIVOT, 15, y, 9)])
    return combine(combine(base, forks), [bore_y(HEAD_OFFSET, HEAD_PIVOT, 4.5)], BRepAlgoAPI_Cut)


def cable_clearance():
    # Straight plug envelope based on the rear connector drawing. Leave a
    # relaxed cable loop beyond this volume and confirm the actual plug body.
    return bore_x(*M12_PORT, 11, CAMERA_MATE_X-52, 53)


def camera_carrier():
    # Y is the tilt axis. The bridge passes above the rear connectors.
    pivot = bore_y(0, 0, 15, -8.5, 17)
    arm = prism([(0, -8.5, -10), (15, -8.5, 17), (CAMERA_MATE_X-8, -8.5, 18),
                 (CAMERA_MATE_X-8, -8.5, 27), (15, -8.5, 27), (0, -8.5, 12)], (0, 17, 0))
    bridge = box(CAMERA_MATE_X-10, -49, 17.5, 10, 98, 10.5)
    pads = [box(CAMERA_MATE_X-10, y-8, 8, 10, 16, 22) for y in (-37.5, 37.5)]
    body = combine(pivot, [arm, bridge, *pads])
    return combine(body, [bore_y(0,0,4.5), cable_clearance(),
                          *(bore_x(y,MOUNT_HOLE_Z,2.25,CAMERA_MATE_X-12,15) for y in (-37.5,37.5))],
                   BRepAlgoAPI_Cut)


def placed(shape, xyz=(0,0,0), degrees=0, axis=(0,1,0)):
    t = gp_Trsf()
    t.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(*axis)),math.radians(degrees))
    t.SetTranslationPart(gp_Vec(*xyz))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()


def bounds(shape):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape,b)
    return b.CornerMin().Coord(), b.CornerMax().Coord()


def volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def interference(first, second):
    common = BRepAlgoAPI_Common(first, second)
    if not common.IsDone():
        raise ValueError('CAD interference check failed')
    return abs(volume(common.Shape()))


def write_step(parts, path):
    assembly = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(assembly)
    for part in parts.values():
        if not BRepCheck_Analyzer(part).IsValid():
            raise ValueError('Invalid assembly geometry')
        builder.Add(assembly, part)
    writer = STEPControl_Writer()
    if (writer.Transfer(assembly,STEPControl_AsIs) != IFSelect_RetDone
            or writer.Write(str(path)) != IFSelect_RetDone):
        raise RuntimeError('Could not write assembly STEP')


def parts_for(d):
    inside, outside = board_collar(d)
    return {
        'oberteil': top_clamp(d), 'unterbacke': lower_clamp(d),
        'board_schelle_innen': inside, 'board_schelle_aussen': outside,
        'board_schieber': board_slider(d), 'kamerakopf_rohr': tilt_shoe(d),
        'kamerakopf_traeger': camera_carrier(), 'passprobe_tisch': edge_gauge(d),
    }


def assembly_for(d, printed):
    top_of_rod = 4+d.rod_length
    pivot = (ROD_X+HEAD_OFFSET, 0, top_of_rod+HEAD_PIVOT-2)
    assembled = {name:shape for name,shape in printed.items()
                 if not name.startswith(('passprobe','kamerakopf'))}
    assembled['kamerakopf_rohr'] = placed(printed['kamerakopf_rohr'], (ROD_X,0,top_of_rod-2))
    assembled['kamerakopf_traeger'] = placed(printed['kamerakopf_traeger'], pivot, d.tilt)
    assembled['stahlrohr'] = cylinder(ROD_X, 0, 4, 9.5, d.rod_length)
    assembled['holzplatte_referenz'] = box(0, -245, -d.table, 110, 490, d.table)
    assembled['stahlprofil_referenz'] = box(d.setback, -245, d.rail_bottom, d.rail, 490, d.rail)
    assembled['stahl_gegenplatte'] = box(d.setback+1, -STRAP_HALF_WIDTH,
                                        d.rail_bottom-BOTTOM_STEEL,
                                        d.rail-2, 2*STRAP_HALF_WIDTH, BOTTOM_STEEL)
    assembled['charuco_referenz'] = box(BOARD_BACK_X, -225, BOARD_BOTTOM,
                                       d.board, 450, d.board_height)
    # Camera reference is the exterior envelope, positioned from the rear M4 datum.
    camera = box(CAMERA_MATE_X, -72.4, MOUNT_HOLE_Z-11.5-21.25, 67.34, 144.8, 42.5)
    assembled['oak_4d_referenz'] = placed(camera, pivot, d.tilt)
    for index, y in enumerate(PULL_ROWS, start=1):
        assembled[f'm8_zugschraube_{index}'] = cylinder(PULL_X, y, d.rail_bottom-36, 4, 140)
    return assembled


def audit(d, parts, assembly):
    checked = [
        ('oberteil', 'holzplatte_referenz'), ('unterbacke', 'stahlprofil_referenz'),
        ('oberteil', 'stahlrohr'), ('kamerakopf_rohr','stahlrohr'),
        ('kamerakopf_rohr', 'kamerakopf_traeger'), ('oberteil','charuco_referenz'),
        ('board_schieber','charuco_referenz'), ('board_schelle_innen','charuco_referenz'),
        ('kamerakopf_traeger','oak_4d_referenz'), ('kamerakopf_rohr','oak_4d_referenz'),
        ('unterbacke','stahl_gegenplatte'), ('board_schelle_innen','stahlrohr'),
        ('board_schelle_aussen','stahlrohr'),
    ]
    checked += [(jaw, f'm8_zugschraube_{number}') for jaw in ('oberteil','unterbacke')
                for number in (1,2)]
    result={}
    for a,b in checked:
        clash=interference(assembly[a],assembly[b])
        if clash > .05:
            raise ValueError(f'Interference: {a} / {b}: {clash:.2f} mm³')
        result[f'{a} / {b}']=clash
    pivot = (ROD_X + HEAD_OFFSET, 0, 4+d.rod_length+HEAD_PIVOT-2)
    camera = box(CAMERA_MATE_X, -72.4, MOUNT_HOLE_Z-11.5-21.25, 67.34, 144.8, 42.5)
    for angle in range(25, 66):
        clearance = placed(cable_clearance(), pivot, angle)
        candidates = (placed(parts['kamerakopf_traeger'], pivot, angle),
                      placed(camera, pivot, angle), clearance)
        clash = max(interference(assembly['kamerakopf_rohr'], item) for item in candidates)
        if clash > .05:
            raise ValueError(f'Hinge, enclosure or plug interference at {angle} degrees: {clash:.2f} mm³')
        result[f'tilt_{angle}_deg']=clash
    result['M12_plug_to_carrier'] = interference(parts['kamerakopf_traeger'], cable_clearance())
    if result['M12_plug_to_carrier'] > .05:
        raise ValueError('M12 keepout intersects carrier')
    slider = assembly['board_schieber']
    board = assembly['charuco_referenz']
    lifted = placed(slider,(0,0,28))
    raised = placed(board,(0,0,17))
    removal = 0.
    # First open the top, then lift over the two lower lips and move inwards.
    for lift in range(0,29,2):
        removal = max(removal,interference(placed(slider,(0,0,lift)),board))
    guides = (lifted, assembly['oberteil'], assembly['board_schelle_innen'])
    for lift in (*range(0,17,2),17):
        candidate = placed(board,(0,0,lift))
        removal = max(removal, *(interference(guide,candidate) for guide in guides))
    for travel in range(0,41,5):
        candidate = placed(raised,(travel,0,0))
        removal = max(removal, *(interference(guide,candidate) for guide in guides))
    if removal > .05:
        raise ValueError('Board extraction interferes with its guides')
    result['board_extraction_sampled_path'] = removal
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for label,value in [('table',35),('setback',35),('rail',32),('bore',19.4),
                        ('board',3),('board-height',360),('rod-length',1270),('tilt',60)]:
        parser.add_argument('--'+label,type=float,default=value)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'cad')
    args=parser.parse_args()
    d=Dimensions(args.table,args.setback,args.rail,args.bore,args.board,args.board_height,
                 args.rod_length,args.tilt)
    if not (28<=d.table<=46 and 25<=d.setback<=47 and 24<=d.rail<=39
            and 19.1<=d.bore<=20.0 and 2.5<=d.board<=4. and 300<=d.board_height<=450
            and 850<=d.rod_length<=1400 and 25<=d.tilt<=65):
        parser.error('Parameters outside the validated modelling envelope')
    args.output.mkdir(parents=True,exist_ok=True)
    parts=parts_for(d)
    assembled=assembly_for(d,parts)
    overlaps=audit(d,parts,assembled)
    stl=[]
    for name,shape in parts.items():
        rotation=90 if name in ('passprobe_tisch','board_schieber','kamerakopf_traeger') else 0
        print_shape=placed(shape,degrees=rotation,axis=(1,0,0))
        lo,_=bounds(print_shape)
        print_shape=placed(print_shape,tuple(-v for v in lo))
        export(print_shape,args.output/name,step=False)
        stl.append(dict(name=name,size_mm=[round(b-a,3) for a,b in zip(*bounds(print_shape))],
                        volume_cm3=round(volume(print_shape)/1000,3)))
    write_step(assembled,args.output/'oak4d-tischklemme.step')
    (args.output/'cad-pruefung.json').write_text(json.dumps(
        dict(parameter_mm=d.__dict__, print_parts=stl, overlaps_mm3=overlaps),
        indent=2)+'\n')


if __name__=='__main__':
    main()
