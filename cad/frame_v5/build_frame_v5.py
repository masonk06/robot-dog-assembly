"""V5 hip-roll canopy and windowed side bracing, within a 180 mm print bed.

Builds a separate revision from V4. Each fixed hip-roll case gets a 4 mm
roof, an inner side frame with a large wire/service window, and a top tie
into its reinforced screw flange. Original mounting holes are untouched.
"""
import json
import sys
from pathlib import Path

CAD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAD / 'frame_v3'))
sys.path.insert(0, str(CAD / 'frame_v4'))
import build_frame_v3 as b
from build_frame_v4 import placed
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

OUT = Path(__file__).resolve().parent


def side_window(x, y):
    # Make a rounded rectangle in XY and rotate it upright into XZ.
    shape = b.rounded(x, 10, 0, 24, 29, 7, 3)
    rotation = gp_Trsf()
    rotation.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 3.141592653589793 / 2)
    upright = BRepBuilderAPI_Transform(shape, rotation, True).Shape()
    shift = gp_Trsf()
    shift.SetTranslation(gp_Vec(0, y + 6, 0))
    return BRepBuilderAPI_Transform(upright, shift, True).Shape()


def main():
    base = b.load(CAD / 'frame_v4' / 'Frame_V4_Reinforced.step')
    frame = base
    added_parts = {}
    for end in ('front', 'rear'):
        # Each roof covers the inner 34.7 mm of the 38 mm fixed case. The
        # outer nose stays open; roofing the entire case plus wall thickness
        # at both ends would exceed 180 mm. End faces stay open for access.
        x = -73.5 if end == 'front' else 63.5
        panel_x = -70 if end == 'front' else 64
        window_x = -65 if end == 'front' else 71
        tie_x = -38.5 if end == 'front' else 63.5
        for side in ('left', 'right'):
            y = -90 if side == 'left' else 60.5
            panel_y = -64.5 if side == 'left' else 60.5
            roof = b.rounded(x, y, 52.5, 40, 29.5, 4, 2)
            panel = b.box(panel_x, panel_y, 4.8, 36, 4, 48)
            panel = b.cut(panel, side_window(window_x, panel_y))
            tie = b.box(tie_x, y + .2, 49.8, 5, 29.1, 3)
            added = b.fuse(b.fuse(roof, panel), tie)
            added_parts[f'{end}_{side}_canopy'] = added
            frame = b.fuse(frame, added)
            print(f'Built {end} {side} canopy', flush=True)
    if not BRepCheck_Analyzer(frame).IsValid() or b.count_solids(frame) != 1:
        raise RuntimeError('Frame must be one valid solid')
    lo, hi = b.bounds(frame)
    size = [round(hi[i] - lo[i], 4) for i in range(3)]
    if size[0] > 180.001 or size[1] > 180.001:
        raise RuntimeError(f'Bed size exceeded: {size}')
    report = {
        'units': 'mm', 'source': 'frame_v4/Frame_V4_Reinforced.step',
        'valid_solid': True, 'dimensions_mm': size, 'roof_thickness_mm': 4,
        'roof_underside_z_mm': 52.5, 'inner_panel_thickness_mm': 4,
        'wire_service_windows_mm': [24, 29],
        'added_volume_mm3': b.volume(frame) - b.volume(base),
        'static_saved_geometry_overlap_delta_mm3': {}, 'electronics_intersections_mm3': {},
        'limitations': [
            'No FEA, fatigue test, or print-strength validation.',
            'Checks use saved CAD placements; full articulated sweeps and actual cable/plug fit remain unverified.',
            'Roofs partially cover each fixed case; outer noses and outside faces remain open.',
            'Do not add a brim outside the 180 mm usable bed width.',
            'Print roof undersides need slicer bridge/support review; remove support before servo installation.',
        ],
    }
    records = json.loads((CAD / 'RoboDog_placements.json').read_text())['parts']
    case = b.load(CAD / 'revision_sources' / 'STS3215_case_fixed.step')
    disc = b.load(CAD / 'revision_sources' / 'STS3215_discs_output.step')
    shapes = {}
    # Check every saved servo housing and its output discs, plus the moving
    # printed roll bracket. A pass does not certify unmodelled wire bends.
    for record in records:
        name = record['name']
        if '_servo_' in name:
            shapes[name + '_case'] = placed(case, record['transform'])
            shapes[name + '_disc'] = placed(disc, record['transform'])
        elif name.endswith('_hip_roll'):
            source = b.load(CAD / 'solid_sources' / 'Part Studio 1 - Hip Roll V3.step')
            shapes[name] = placed(source, record['transform'])
    for name, shape in shapes.items():
        before = b.volume(b.boolean(BRepAlgoAPI_Common, base, shape))
        after = b.volume(b.boolean(BRepAlgoAPI_Common, frame, shape))
        delta = after - before
        report['static_saved_geometry_overlap_delta_mm3'][name] = round(delta, 6)
        if delta > .01:
            raise RuntimeError(f'Added collision with {name}: {delta} mm3')
        print(f'Checked {name}', flush=True)
    references = {
        'Battery_75x34x25_REFERENCE': b.rounded(-22.5, -17, 5.8, 75, 34, 25, 2),
        'Jetson_103x90p5x34p77_REFERENCE': b.box(-36.5, -45.25, 40, 103, 90.5, 34.77),
        'Waveshare_42x33_REFERENCE': b.box(-6, 25, 13, 42, 33, 17),
    }
    tray = b.load(CAD / 'frame_v3' / 'Jetson_Tray.step')
    sled = b.load(CAD / 'frame_v3' / 'Waveshare_Sled.step')
    for name, shape in {**references, 'Jetson_Tray': tray, 'Waveshare_Sled': sled}.items():
        overlap = b.volume(b.boolean(BRepAlgoAPI_Common, frame, shape))
        report['electronics_intersections_mm3'][name] = round(overlap, 6)
        if overlap > .01:
            raise RuntimeError(f'New frame hits {name}: {overlap} mm3')
    b.COLORS['Frame_V5'] = (.39, .49, .58)
    b.write_step(OUT / 'Frame_V5_Servo_Canopies.step', {'Frame_V5': frame})
    BRepMesh_IncrementalMesh(frame, .15, False, .25, True)
    writer = StlAPI_Writer()
    if not writer.Write(frame, str(OUT / 'Frame_V5_Servo_Canopies.stl')):
        raise RuntimeError('STL export failed')
    assembly = {'Frame_V5': frame, 'Jetson_Tray': tray, 'Waveshare_Sled': sled}
    b.write_step(OUT / 'RoboDog_Frame_V5_Assembly.step', assembly)
    b.render(OUT / 'Frame_V5_preview.png', {'Frame_V5': frame}, 'RoboDog V5 | servo roofs and windowed side bracing', (35, -48))
    b.render(OUT / 'Frame_V5_top.png', {'Frame_V5': frame}, 'V5 | four reinforced servo pockets', (72, -45))
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
