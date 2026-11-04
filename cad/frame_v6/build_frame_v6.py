"""RoboDog V6: V5 reinforced frame with a Pi 5 and modular power mounting.

Millimetres. Uses OCP/numpy/matplotlib and the checked-in V3/V5 sources.
Generic power envelopes are space reservations, not verified purchased parts.
"""
import json
import sys
import uuid
from pathlib import Path

CAD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAD / 'frame_v3'))
sys.path.insert(0, str(CAD / 'frame_v4'))
import build_frame_v3 as b
from build_frame_v4 import placed
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer

OUT = Path(__file__).resolve().parent
PI_ORIGIN = (-27.5, -36, 46)
PI_HOLES = [(-24, -32.5), (34, -32.5), (-24, 16.5), (34, 16.5)]
POWER_POSTS = [(-23, -28), (53, -28)]


def write_assembly(path, parts):
    # Export to a fresh path first: some Windows viewers retain a lock on an
    # already-open STEP file. Never leave a previously delivered file partial.
    temporary = path.with_name(path.stem + '_' + uuid.uuid4().hex[:8] + '.step')
    b.write_step(temporary, parts)
    try:
        temporary.replace(path)
        return path
    except PermissionError:
        print('Existing CAD file is in use; fresh export: ' + str(temporary), flush=True)
        return temporary


def finish_exports():
    """Finish visual/assembly exports from already validated individual solids."""
    report = json.loads((OUT / 'validation.json').read_text())
    if not any('IMU_' in key for key in report['packaging_intersections_mm3']):
        raise RuntimeError('Latest sensor-pad geometry has not been checked')
    parts = {name: b.load(OUT / f'{name}.step') for name in
             ('Frame_V6', 'Pi5_Electronics_Deck', 'Power_Distribution_Sled', 'Waveshare_Sled')}
    b.COLORS.update({'Frame_V6': (.40, .49, .57), 'Pi5_Electronics_Deck': (.15, .48, .53),
                     'Power_Distribution_Sled': (.75, .42, .14),
                     'Pi5_and_Cooler_REFERENCE': (.18, .49, .25),
                     'Regulator_50x28x20_RESERVED': (.37, .48, .76),
                     'Fused_Distribution_60x20x18_RESERVED': (.77, .48, .14),
                     'Switch_16x16x20_RESERVED': (.64, .23, .25),
                     'IMU_25x18x10_RESERVED': (.55, .37, .68)})
    refs = {
        'Battery_75x34x25_REFERENCE': b.rounded(-22.5, -17, 5.8, 75, 34, 25, 2),
        'Pi5_and_Cooler_REFERENCE': b.box(*PI_ORIGIN, 85, 56, 28),
        'Waveshare_42x33_REFERENCE': b.box(-6, 25, 13, 42, 33, 17),
        'Regulator_50x28x20_RESERVED': b.box(-21, 29, 44, 50, 28, 20),
        'Fused_Distribution_60x20x18_RESERVED': b.box(-15, -46, 16, 60, 20, 18),
        'Switch_16x16x20_RESERVED': b.box(39, 33, 40, 16, 16, 20),
        'IMU_25x18x10_RESERVED': b.box(-58, -9, 6, 25, 18, 10),
    }
    report['assembly_exports'] = [str(write_assembly(OUT / 'RoboDog_V6_Complete.step', parts).name),
        str(write_assembly(OUT / 'RoboDog_V6_Equipment_Layout.step', {**parts, **refs}).name)]
    b.render(OUT / 'Frame_V6_assembly.png', parts, 'RoboDog V6 | Pi 5 and modular power deck', (40, -48))
    b.render(OUT / 'Frame_V6_layout.png', {**parts, **refs}, 'V6 | electronics and power space reservations', (62, -55))
    b.render(OUT / 'Frame_V6_lower_deck.png', {'Frame_V6': parts['Frame_V6'],
             'Power_Distribution_Sled': parts['Power_Distribution_Sled'],
             'Waveshare_Sled': parts['Waveshare_Sled'],
             'Battery_75x34x25_REFERENCE': refs['Battery_75x34x25_REFERENCE'],
             'IMU_25x18x10_RESERVED': refs['IMU_25x18x10_RESERVED']},
             'V6 lower deck | battery, Waveshare, power and IMU mounts', (67, -48))
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Complete assemblies and previews exported successfully.')


def export_part(name, shape):
    valid, count = BRepCheck_Analyzer(shape).IsValid(), b.count_solids(shape)
    if not valid or count != 1:
        raise RuntimeError(f'{name}: valid={valid}, solid_count={count}')
    lo, hi = b.bounds(shape)
    size = [round(hi[i] - lo[i], 4) for i in range(3)]
    if size[0] > 180 or size[1] > 180:
        raise RuntimeError(f'{name} exceeds bed: {size}')
    b.write_step(OUT / f'{name}.step', {name: shape})
    BRepMesh_IncrementalMesh(shape, .15, False, .25, True)
    writer = StlAPI_Writer()
    if not writer.Write(shape, str(OUT / f'{name}.stl')):
        raise RuntimeError(f'Cannot export STL: {name}')
    return {'valid': valid, 'solids': count, 'dimensions_mm': size, 'bounds_mm': [lo, hi]}


def overlap(a, c):
    return b.volume(b.boolean(BRepAlgoAPI_Common, a, c))


def main():
    base = b.load(CAD / 'frame_v5' / 'Frame_V5_Servo_Canopies.step')
    frame = base
    for x, y in POWER_POSTS:
        frame = b.fuse(frame, b.cyl(x, y, 4.8, 4.5, 8.2))
        frame = b.cut(frame, b.cyl(x, y, 6, 1.3, 8))
    # Small dedicated IMU pad beside the battery, rigidly tied to the floor.
    # Generic 25 x 18 mm sensor allowance; use thin insulating mounting tape.
    frame = b.fuse(frame, b.rounded(-60, -12, 4.8, 30, 24, 1.2, 3))
    for x in (-62, -30):
        frame = b.cut(frame, b.rounded(x, -8, -1, 2, 16, 8, .8))
    # Trim only the outermost 0.1 mm in Y. Original flange faces stop at
    # |Y|=89.8485, so screw-hole seating surfaces remain within the trim.
    frame = b.boolean(BRepAlgoAPI_Common, frame, b.box(-80, -89.9, -1, 190, 179.8, 85))
    print('Built V6 base and lower power-sled supports', flush=True)
    # Same four chassis attachments as V3; a new open Pi tray replaces Jetson.
    deck = b.rounded(-47, -53, 37, 124, 112, 3, 5)
    # Open underside for airflow/storage access, away from the Pi pillars.
    deck = b.cut(deck, b.rounded(-15, -25, 36, 40, 33, 5, 3))
    for x, y in b.POSTS:
        deck = b.cut(deck, b.cyl(x, y, 36, 1.7, 5))
    for x, y in PI_HOLES:
        deck = b.fuse(deck, b.cyl(x, y, 39.8, 3.4, 6.2))
        # M2.5 clearance holes through deck and pillar. Fit a screw from below
        # with suitable nuts, or use separate threaded standoffs of same rise.
        deck = b.cut(deck, b.cyl(x, y, 36, 1.35, 11))
    # Generic regulator mount: parallel adjustable slots on a solid platform.
    for y in (32, 51):
        deck = b.cut(deck, b.rounded(-19, y, 36, 47, 3.2, 5, 1.5))
    # Switch/auxiliary service corner: universal fastener/strap slots, no
    # guessed switch cutout. A mounting adapter can be added after selection.
    for x in (36, 56):
        deck = b.cut(deck, b.rounded(x, 30, 36, 3.2, 23, 5, 1.5))
    for x in (-38, 62):
        deck = b.cut(deck, b.rounded(x, -20, 36, 5, 32, 5, 2))
    # Two generic electronics spacers for insulating regulator mounting.
    spacers = {}
    spacer = b.cut(b.cyl(0, 0, 0, 3.5, 4), b.cyl(0, 0, -1, 1.7, 6))
    # Lower power sled remains above the original floor rib and below Pi tray.
    power = b.rounded(-28, -49, 13, 86, 26, 3, 3)
    for x, y in POWER_POSTS:
        power = b.cut(power, b.cyl(x, y, 12, 1.7, 5))
    for x in (-19, 46):
        power = b.cut(power, b.rounded(x, -45, 12, 3, 15, 5, 1.3))
    # Cooling and universal attachment grid for a compact fuse/distribution
    # module. Its actual terminals and electrical rating must be selected.
    for x in (-9, 10, 29):
        power = b.cut(power, b.rounded(x, -42, 12, 10, 3, 5, 1.3))
    waveshare = b.load(CAD / 'frame_v3' / 'Waveshare_Sled.step')
    parts = {'Frame_V6': frame, 'Pi5_Electronics_Deck': deck,
             'Power_Distribution_Sled': power, 'Waveshare_Sled': waveshare}
    b.COLORS.update({'Frame_V6': (.40, .49, .57), 'Pi5_Electronics_Deck': (.15, .48, .53),
                     'Power_Distribution_Sled': (.75, .42, .14), 'Regulator_Spacer': (.55, .57, .62),
                     'Pi5_and_Cooler_REFERENCE': (.18, .49, .25),
                     'Regulator_50x28x20_RESERVED': (.37, .48, .76),
                     'Fused_Distribution_60x20x18_RESERVED': (.77, .48, .14),
                     'Switch_16x16x20_RESERVED': (.64, .23, .25)})
    b.COLORS['IMU_25x18x10_RESERVED'] = (.55, .37, .68)
    refs = {
        'Battery_75x34x25_REFERENCE': b.rounded(-22.5, -17, 5.8, 75, 34, 25, 2),
        # Conservative whole-board/cooler volume, not detailed vendor geometry.
        'Pi5_and_Cooler_REFERENCE': b.box(*PI_ORIGIN, 85, 56, 28),
        'Waveshare_42x33_REFERENCE': b.box(-6, 25, 13, 42, 33, 17),
        'Regulator_50x28x20_RESERVED': b.box(-21, 29, 44, 50, 28, 20),
        'Fused_Distribution_60x20x18_RESERVED': b.box(-15, -46, 16, 60, 20, 18),
        'Switch_16x16x20_RESERVED': b.box(39, 33, 40, 16, 16, 20),
        'IMU_25x18x10_RESERVED': b.box(-58, -9, 6, 25, 18, 10),
    }
    report = {'units': 'mm', 'baseline': 'frame_v5/Frame_V5_Servo_Canopies.step',
              'parts': {}, 'printed_part_intersections_mm3': {}, 'packaging_intersections_mm3': {},
              'saved_servo_case_additional_overlap_mm3': {},
              'pi_board_mm': [85, 56], 'pi_hole_pitch_mm': [58, 49],
              'pi_holes_xy_mm': PI_HOLES, 'pi_mount_board_z_mm': 46,
              'generic_power_mounts': 'reserved envelopes only; no regulator/fuse/switch hardware selected',
              'limitations': ['No load/fatigue or thermal test.',
                              'Full joint sweeps, actual purchased enclosure, cables, and plugs unverified.',
                              'Pi mounts as bare board with cooler; the eBay enclosure is not modelled.',
                              'Power electronics reservations require actual dimensions and terminal clearances before purchase.',
                              '5V regulator rating alone does not verify Pi 5 USB-C power negotiation.',
                              'Servo power distribution must be rated for measured motor current; do not route all motor power through the 5A Waveshare adapter.']}
    # All printable bodies and all occupied/reserved volumes checked in the
    # assembled positions. Zero-volume contact at mounting planes is allowed.
    for i, (name, shape) in enumerate(parts.items()):
        for other, other_shape in list(parts.items())[i + 1:]:
            value = overlap(shape, other_shape)
            report['printed_part_intersections_mm3'][f'{name} vs {other}'] = round(value, 6)
            if value > .01:
                raise RuntimeError(f'Printed-part interference: {name}, {other}: {value}')
    for name, shape in refs.items():
        for other, other_shape in parts.items():
            value = overlap(shape, other_shape)
            report['packaging_intersections_mm3'][f'{name} vs {other}'] = round(value, 6)
            if value > .01:
                raise RuntimeError(f'Packaging interference: {name}, {other}: {value}')
    for i, (name, shape) in enumerate(refs.items()):
        for other, other_shape in list(refs.items())[i + 1:]:
            if overlap(shape, other_shape) > .01:
                raise RuntimeError(f'Packaging envelopes intersect: {name}, {other}')
    # Since V5 already checks the unchanged canopies against all saved moving
    # pieces, check only the two new floor posts against every servo case.
    records = json.loads((CAD / 'RoboDog_placements.json').read_text())['parts']
    case = b.load(CAD / 'revision_sources' / 'STS3215_case_fixed.step')
    for r in records:
        if '_servo_' in r['name']:
            shape = placed(case, r['transform'])
            for name, printed in parts.items():
                value = overlap(printed, shape)
                if name == 'Frame_V6':
                    value -= overlap(base, shape)
                report['saved_servo_case_additional_overlap_mm3'][f'{name} vs {r["name"]}'] = round(value, 6)
                if value > .01:
                    raise RuntimeError(f'Added servo overlap: {name}, {r["name"]}: {value}')
            print('Checked ' + r['name'], flush=True)
    for name, shape in parts.items():
        report['parts'][name] = export_part(name, shape)
    report['parts']['Regulator_Spacer'] = export_part('Regulator_Spacer', spacer)
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    finish_exports()
    print(json.dumps(report['parts'], indent=2))


if __name__ == '__main__':
    if '--finish-exports' in sys.argv:
        finish_exports()
    else:
        main()
