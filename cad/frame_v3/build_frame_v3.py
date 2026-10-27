"""Build the RoboDog V3 electronics-frame revision from the original STEP.

Dimensions are millimetres. Requires OCP, numpy, matplotlib. The original
170 x 180 mm perimeter and all geometry at |Y| >= 60 mm are protected.
This is a separate CAD revision; existing assemblies and servo tools are
never modified. Run with the system Python that already has OCP installed.
"""
import json
import math
from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakePrism
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

OUT = Path(__file__).resolve().parent
CAD = OUT.parent
SOURCE = CAD / 'solid_sources' / 'FRAME V2.step'
POSTS = [(-42, -44), (-42, 44), (72, -44), (72, 44)]
COLORS = {'Frame_V3': (.19, .25, .32), 'Jetson_Tray': (.16, .49, .57),
          'Waveshare_Sled': (.76, .47, .17), 'Battery_75x34x25_REFERENCE': (.83, .22, .22),
          'Jetson_103x90p5x34p77_REFERENCE': (.35, .62, .27),
          'Waveshare_42x33_REFERENCE': (.24, .31, .22)}


def load(path):
    r = STEPControl_Reader()
    if int(r.ReadFile(str(path))) != 1:
        raise RuntimeError(f'Cannot read {path}')
    r.TransferRoots()
    return r.OneShape()


def box(x, y, z, dx, dy, dz):
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()


def cyl(x, y, z, radius, height):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 0, 1)), radius, height).Shape()


def boolean(cls, a, b):
    op = cls(a, b)
    op.SetFuzzyValue(.00001)
    op.Build()
    if not op.IsDone():
        raise RuntimeError(f'{cls.__name__} failed')
    return op.Shape()


def fuse(a, b):
    return boolean(BRepAlgoAPI_Fuse, a, b)


def cut(a, b):
    return boolean(BRepAlgoAPI_Cut, a, b)


def rounded(x, y, z, dx, dy, dz, radius=2):
    shape = fuse(box(x + radius, y, z, dx - 2 * radius, dy, dz),
                 box(x, y + radius, z, dx, dy - 2 * radius, dz))
    for xx in (x + radius, x + dx - radius):
        for yy in (y + radius, y + dy - radius):
            shape = fuse(shape, cyl(xx, yy, z, radius, dz))
    return shape


def gusset(xwall, direction, y):
    wire = BRepBuilderAPI_MakePolygon()
    for x, z in ((xwall, 4.8), (xwall + direction * 16, 4.8), (xwall, 26)):
        wire.Add(gp_Pnt(x, y, z))
    wire.Close()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(), gp_Vec(0, 4, 0)).Shape()


def volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return abs(props.Mass())


def bounds(shape):
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    lo, hi = bbox.CornerMin(), bbox.CornerMax()
    return [[round(v, 4) for v in (lo.X(), lo.Y(), lo.Z())],
            [round(v, 4) for v in (hi.X(), hi.Y(), hi.Z())]]


def count_solids(shape):
    count, explorer = 0, TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def write_step(path, parts):
    doc = TDocStd_Document(TCollection_ExtendedString('MDTV-XCAF'))
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    for name, shape in parts.items():
        label = tool.AddShape(shape, False)
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))
        rgb = COLORS.get(name, (.6, .6, .6))
        color_tool.SetColor(label, Quantity_Color(*rgb, Quantity_TOC_RGB), XCAFDoc_ColorType.XCAFDoc_ColorGen)
    writer = STEPCAFControl_Writer()
    writer.SetColorMode(True)
    writer.SetNameMode(True)
    writer.Transfer(doc, STEPControl_AsIs)
    if int(writer.Write(str(path))) != 1:
        raise RuntimeError(f'Cannot write {path}')


def triangles(shape):
    BRepMesh_IncrementalMesh(shape, .35, False, .35, True)
    explorer, output = TopExp_Explorer(shape, TopAbs_FACE), []
    while explorer.More():
        face = TopoDS.Face(explorer.Current())
        location = TopLoc_Location()
        mesh = BRep_Tool.Triangulation_s(face, location)
        if mesh is not None:
            transform = location.Transformation()
            for index in range(1, mesh.NbTriangles() + 1):
                ids = mesh.Triangle(index).Get()
                output.append([[mesh.Node(i).Transformed(transform).X(),
                                mesh.Node(i).Transformed(transform).Y(),
                                mesh.Node(i).Transformed(transform).Z()] for i in ids])
        explorer.Next()
    return np.array(output)


def render(path, parts, title, elevations=(32, -48)):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(11, 9), facecolor='#f5f6f8')
    ax = fig.add_subplot(111, projection='3d', facecolor='#f5f6f8')
    all_faces, all_colors = [], []
    for name, shape in parts.items():
        faces = triangles(shape)
        normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        normals /= np.maximum(lengths, 1e-12)[:, None]
        light = np.array([-.3, -.4, .85])
        shade = .68 + .32 * np.abs(normals @ light)
        colors = np.column_stack((np.array(COLORS[name])[None, :] * shade[:, None], np.ones(len(faces))))
        all_faces.extend(faces)
        all_colors.extend(colors)
    # One collection sorts individual triangles across parts, avoiding the
    # incorrect occlusion that separate 3D collections produce in matplotlib.
    ax.add_collection3d(Poly3DCollection(all_faces, facecolors=all_colors, edgecolors='none'))
    ax.set_xlim(-85, 115)
    ax.set_ylim(-100, 100)
    ax.set_zlim(-5, 105)
    ax.set_box_aspect((200, 200, 110))
    ax.view_init(*elevations)
    ax.set_axis_off()
    ax.set_title(title, fontsize=15, pad=15)
    fig.text(.5, .07, 'Mounts retained | centered battery | removable electronics trays', ha='center', color='#45505c')
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    original = load(SOURCE)
    frame = original
    # Rounded internal rails and four triangular wall braces. All stay inside
    # the protected servo zones. The original external walls are untouched.
    for y in (-47, 41):
        frame = fuse(frame, rounded(-64.5, y, 4.8, 159, 6, 8.2, 2))
    for x, direction in ((-64.9, 1), (94.9, -1)):
        for y in (-39, 35):
            frame = fuse(frame, gusset(x, direction, y))
    # Battery cradle: 79 x 38 mm inside, for the user's 75 x 34 x 25 pack.
    # Low rounded stops let the battery come out vertically after tray removal.
    cradle = rounded(-27, -21, 4.8, 84, 42, 8.2, 3)
    cradle = cut(cradle, rounded(-24.5, -19, 4, 79, 38, 10, 1.5))
    frame = fuse(frame, cradle)
    # Four blind-pilot tray supports rise from the ribbed floor.
    for x, y in POSTS:
        frame = fuse(frame, cyl(x, y, 4.8, 4.5, 32.2))
        frame = cut(frame, cyl(x, y, 25, 1.3, 13))
    # Two 15 mm battery straps pass through paired rounded floor slots.
    for x in (-12, 27):
        for y in (-27, 24):
            frame = cut(frame, rounded(x, y, -1, 16, 3, 7, 1))
    # Radiused cable pass-throughs in the central floor, away from all mounts.
    for y in (-37, 32):
        for x in (-16, 25):
            frame = cut(frame, rounded(x, y, -1, 20, 5, 7, 2))
    # Open Jetson tray: no wall in front of any board edge or above the fan.
    tray = rounded(-47, -53, 37, 124, 106, 3, 6)
    tray = cut(tray, rounded(-24, -27, 36, 78, 54, 5, 5))
    for x, y in POSTS:
        tray = cut(tray, cyl(x, y, 36, 1.7, 5))
    # Adjustable slots, NOT an assertion of the unverified native PCB pattern.
    for x in (-39, 57):
        for y in (-35, 32):
            tray = cut(tray, rounded(x, y, 36, 12, 3.4, 5, 1.6))
    for y in (-44, 40):
        tray = cut(tray, rounded(-8, y, 36, 46, 4, 5, 1.8))
    # Waveshare removable sled cantilevers 9.5 mm beyond the central floor;
    # its inner two fasteners are accessible with the Jetson tray removed.
    # Relieve only the added internal rib below the sled so the removable
    # pieces fit without overlapping. Leave the battery cradle wall intact.
    frame = cut(frame, rounded(-9.3, 21.7, 5, 48.6, 39.6, 8.5, 3))
    sled = rounded(-9, 22, 5, 48, 39, 3, 3)
    for x in (-3.5, 33.5):
        for y in (27.5, 55.5):
            sled = fuse(sled, cyl(x, y, 7.8, 3, 5.2))
            sled = cut(sled, cyl(x, y, 7.5, 1.1, 7))
    for x in (-4, 34):
        # M3 screw-clearance holes through sled; blind floor pilot below.
        sled = cut(sled, cyl(x, 39.5, 4, 1.7, 5))
        frame = cut(frame, cyl(x, 39.5, 1.8, 1.3, 4))
    # Reference solids represent packaging volumes, not vendor component CAD.
    references = {
        'Battery_75x34x25_REFERENCE': rounded(-22.5, -17, 5.8, 75, 34, 25, 2),
        'Jetson_103x90p5x34p77_REFERENCE': box(-36.5, -45.25, 40, 103, 90.5, 34.77),
        'Waveshare_42x33_REFERENCE': box(-6, 25, 13, 42, 33, 17),
    }
    parts = {'Frame_V3': frame, 'Jetson_Tray': tray, 'Waveshare_Sled': sled}
    report = {
        'units': 'mm', 'base_source': str(SOURCE.relative_to(CAD)),
        'source_status': 'saved FRAME V2 STEP; live unsaved Fusion geometry not re-exported',
        'battery_user_dimensions': [75, 34, 25], 'battery_cavity_xy': [79, 38],
        'jetson_complete_kit_envelope': [103, 90.5, 34.77],
        'waveshare_pcb': [42, 33], 'waveshare_hole_spacing': [37, 28],
        'jetson_mount': 'adjustable slots; native hole positions require physical fit check',
        'parts': {}, 'protected_mount_zones': [], 'reference_collisions_mm3': {},
        'limitations': [
            'Not structurally load-tested or FEA validated.',
            'Servo and cable clearances use saved placements; no swept joint-motion validation.',
            'Connector plug sizes/bend radii vary; side corridors are reserved, not vendor cable CAD.',
            'Jetson reference is the whole dev-kit packaging envelope, not exact board geometry.',
            'Mount posts use 2.6 mm pilot holes for suitable M3 plastic-fastening hardware; confirm printed fit.',
            'Waveshare uses 2.2 mm pilot holes for M2 hardware into printed bosses; PCB holes are 2.5 mm.',
        ],
    }
    for name, shape in parts.items():
        valid = BRepCheck_Analyzer(shape).IsValid()
        solids = count_solids(shape)
        report['parts'][name] = {'valid': valid, 'solids': solids, 'bounds': bounds(shape), 'solid_volume_mm3': volume(shape)}
        if not valid or solids != 1:
            raise RuntimeError(f'{name}: invalid or disconnected ({solids} solids)')
        write_step(OUT / f'{name}.step', {name: shape})
        BRepMesh_IncrementalMesh(shape, .15, False, .25, True)
        writer = StlAPI_Writer()
        if not writer.Write(shape, str(OUT / f'{name}.stl')):
            raise RuntimeError(f'Cannot write {name} STL')
    # Exact subtraction/common check confirms all original material in the
    # four outer servo mounting regions is preserved and nothing is added.
    for y in (-100, 60):
        region = box(-80, y, -5, 190, 40, 100)
        old = boolean(BRepAlgoAPI_Common, original, region)
        new = boolean(BRepAlgoAPI_Common, frame, region)
        delta = volume(cut(old, new)) + volume(cut(new, old))
        report['protected_mount_zones'].append({'y_range': [y, y + 40], 'symmetric_difference_mm3': delta})
        if delta > .01:
            raise RuntimeError(f'Mount zone changed by {delta} mm3')
    report['printed_part_intersections_mm3'] = {}
    pairs = list(parts.items())
    for i, (a_name, a_shape) in enumerate(pairs):
        for b_name, b_shape in pairs[i + 1:]:
            overlap = volume(boolean(BRepAlgoAPI_Common, a_shape, b_shape))
            report['printed_part_intersections_mm3'][a_name + ' vs ' + b_name] = round(overlap, 6)
            if overlap > .01:
                raise RuntimeError(f'Printed parts interfere: {a_name}, {b_name}: {overlap}')
    for reference, shape in references.items():
        for name, part in parts.items():
            overlap = volume(boolean(BRepAlgoAPI_Common, shape, part))
            report['reference_collisions_mm3'][reference + ' vs ' + name] = round(overlap, 6)
            if overlap > .01:
                raise RuntimeError(f'{reference} interferes with {name}: {overlap}')
    # Empty corridor outside each side opening, high enough to pass over floor.
    for side, y in (('front_IO', -80), ('rear_cables', 60)):
        corridor = box(-30, y, 16, 90, 20, 68)
        report.setdefault('open_side_corridors', {})[side] = round(sum(
            volume(boolean(BRepAlgoAPI_Common, corridor, part)) for part in parts.values()), 6)
    report['added_frame_volume_mm3'] = volume(frame) - volume(original)
    write_step(OUT / 'RoboDog_Frame_V3_Assembly.step', parts)
    write_step(OUT / 'RoboDog_Frame_V3_Layout_Reference.step', {**parts, **references})
    (OUT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    render(OUT / 'Frame_V3_preview.png', parts, 'RoboDog V3 | reinforced frame + removable trays')
    render(OUT / 'Frame_V3_packaging.png', {**parts, **references}, 'RoboDog V3 | battery and electronics fit envelopes')
    render(OUT / 'Frame_V3_lower_deck.png', {'Frame_V3': frame, 'Waveshare_Sled': sled,
           'Battery_75x34x25_REFERENCE': references['Battery_75x34x25_REFERENCE']},
           'Lower deck | low battery and accessible servo adapter', (65, -45))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
