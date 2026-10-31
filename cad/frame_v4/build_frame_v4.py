"""Reinforce the four hip-roll screw flanges without moving their holes.

Adds 5 mm behind the original mounting faces by extruding the exact source
faces, including their hole wires and connector openings. Original servo-side
contact faces are retained. Lower gussets connect each flange to a wider foot.
The final printed XY envelope must remain <=180 x 180 mm.
"""
import json
import sys
from pathlib import Path

CAD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAD / 'frame_v3'))
import build_frame_v3 as b
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

OUT = Path(__file__).resolve().parent
DEPTH = 5.0


def placed(shape, matrix):
    tr = gp_Trsf()
    tr.SetValues(*[matrix[i][j] for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(shape, tr, True).Shape()


def brace(x, direction, y):
    polygon = BRepBuilderAPI_MakePolygon()
    for xx, zz in ((x, 4.8), (x + direction * 17, 4.8), (x, 19)):
        polygon.Add(gp_Pnt(xx, y, zz))
    polygon.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(polygon.Wire()).Face(), gp_Vec(0, 4, 0)).Shape()


def main():
    original = b.load(b.SOURCE)
    base = b.load(CAD / 'frame_v3' / 'Frame_V3.step')
    frame = base
    additions = []
    faces = TopExp_Explorer(original, TopAbs_FACE)
    flange_records = []
    while faces.More():
        face = TopoDS.Face(faces.Current())
        lo, hi = b.bounds(face)
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, props)
        # The planar inboard ends of the four original 5 mm mounting flanges.
        # Select geometrically; preserve the original face's exact inner wires.
        front = abs(lo[0] + 38.9774) < .005 and abs(hi[0] + 38.9774) < .005
        rear = abs(lo[0] - 68.9774) < .005 and abs(hi[0] - 68.9774) < .005
        if (front or rear) and props.Mass() > 200 and (lo[1] > 60 or hi[1] < -60):
            direction = 1 if front else -1
            thickener = BRepPrimAPI_MakePrism(face, gp_Vec(direction * DEPTH, 0, 0)).Shape()
            additions.append(thickener)
            flange_records.append({'side': 'front' if front else 'rear', 'face_bounds': [lo, hi],
                                   'added_thickness_mm': DEPTH,
                                   'method': 'exact original face extrusion, retaining bore and aperture wires'})
        faces.Next()
    if len(flange_records) != 4:
        raise RuntimeError(f'Expected four flange faces; found {len(flange_records)}')
    # Broad low feet and two gussets per mount. Keep all braces below Z=19,
    # beneath the lower screw centres (Z=23.5) and the middle connector aperture.
    for x, direction in ((-38.9774, 1), (68.9774, -1)):
        for side in (-1, 1):
            y0 = 64.5 if side == 1 else -90
            foot_x = x if direction == 1 else x - 17
            additions.append(b.rounded(foot_x, y0, .0, 17, 25.5, 5, 2))
            for y in ((65, 85.5) if side == 1 else (-89.5, -69)):
                additions.append(brace(x + direction * 4.8, direction, y))
    # Preserve space occupied by all four fixed hip-roll cases in the saved
    # CAD placements. Keep the original baseline fit; no additional intrusion.
    case = b.load(CAD / 'revision_sources' / 'STS3215_case_fixed.step')
    records = json.loads((CAD / 'RoboDog_placements.json').read_text())['parts']
    cases = {r['name']: placed(case, r['transform']) for r in records if r['name'].endswith('servo_hip_roll')}
    for i, addition in enumerate(additions):
        for case_shape in cases.values():
            if b.volume(b.boolean(BRepAlgoAPI_Common, addition, case_shape)) > .0001:
                addition = b.cut(addition, case_shape)
        frame = b.fuse(frame, addition)
        print(f'Joined reinforcement {i + 1}/{len(additions)}', flush=True)
    if not BRepCheck_Analyzer(frame).IsValid() or b.count_solids(frame) != 1:
        raise RuntimeError('Reinforced frame is invalid or disconnected')
    lo, hi = b.bounds(frame)
    size = [round(hi[i] - lo[i], 4) for i in range(3)]
    if size[0] > 180.001 or size[1] > 180.001:
        raise RuntimeError(f'Frame exceeds print bed: {size}')
    report = {'units': 'mm', 'source_frame': 'frame_v3/Frame_V3.step',
              'failure_report': 'User reports cracks initiating at outside screw holes',
              'flanges': flange_records, 'frame_dimensions': size, 'valid_solid': True,
              'bed_limit': [180, 180], 'added_volume_mm3': b.volume(frame) - b.volume(base),
              'case_overlap_delta_mm3': {}, 'reference_overlap_mm3': {},
              'limitations': ['No structural test/FEA; strength improvement is a design hypothesis.',
                              'Static saved servo geometry checked; full joint sweeps and actual cable bends remain to check.',
                              'Frame reaches 180 mm in Y: a brim/skirt must not extend outside the usable bed.',
                              'Screw holes and servo-side mount faces retain their original size and location.',
                              'Original screw-hole edge distances are retained; added thickness spreads load in depth.']}
    for name, shape in cases.items():
        before = b.volume(b.boolean(BRepAlgoAPI_Common, base, shape))
        after = b.volume(b.boolean(BRepAlgoAPI_Common, frame, shape))
        report['case_overlap_delta_mm3'][name] = after - before
        if after - before > .01:
            raise RuntimeError(f'Additional servo case collision: {name}')
    # Existing electronics packaging, unchanged from V3.
    references = {
        'Battery_75x34x25_REFERENCE': b.rounded(-22.5, -17, 5.8, 75, 34, 25, 2),
        'Jetson_103x90p5x34p77_REFERENCE': b.box(-36.5, -45.25, 40, 103, 90.5, 34.77),
        'Waveshare_42x33_REFERENCE': b.box(-6, 25, 13, 42, 33, 17),
    }
    tray = b.load(CAD / 'frame_v3' / 'Jetson_Tray.step')
    sled = b.load(CAD / 'frame_v3' / 'Waveshare_Sled.step')
    for name, shape in {**references, 'Jetson_Tray': tray, 'Waveshare_Sled': sled}.items():
        overlap = b.volume(b.boolean(BRepAlgoAPI_Common, frame, shape))
        report['reference_overlap_mm3'][name] = overlap
        if overlap > .01:
            raise RuntimeError(f'Reinforcement hits {name}: {overlap}')
    b.COLORS['Frame_V4'] = (.22, .29, .36)
    b.write_step(OUT / 'Frame_V4_Reinforced.step', {'Frame_V4': frame})
    BRepMesh_IncrementalMesh(frame, .15, False, .25, True)
    writer = StlAPI_Writer()
    if not writer.Write(frame, str(OUT / 'Frame_V4_Reinforced.stl')):
        raise RuntimeError('STL export failed')
    parts = {'Frame_V4': frame, 'Jetson_Tray': tray, 'Waveshare_Sled': sled}
    b.write_step(OUT / 'RoboDog_Frame_V4_Assembly.step', parts)
    b.render(OUT / 'Frame_V4_preview.png', {'Frame_V4': frame}, 'RoboDog V4 | reinforced hip-roll screw flanges', (42, -48))
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
