"""Export the current IMX708 adapter as an editable STEP solid for Onshape.

This intentionally mirrors camera_chassis_adapter.scad.  It is not a separate
design: update the two files together whenever changing a fit dimension.
"""
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt


OUT = Path(__file__).with_name("camera_chassis_adapter_imx708_open_top.step")

PLATE_THICKNESS = 3.2
PLATE_WIDTH_Y = 46.0
PLATE_HEIGHT_Z = 21.5
PLATE_CENTER_Z = 26.5
CORNER_RADIUS = 3.0

CHASSIS_HOLES = ((-17.0, 32.0), (17.0, 32.0))
CAMERA_HOLES = ((y, z) for y in (-10.5, 10.5) for z in (22.0, 34.5))


def fuse(left, right):
    operation = BRepAlgoAPI_Fuse(left, right)
    operation.Build()
    if not operation.IsDone():
        raise RuntimeError("Boolean fuse failed")
    return operation.Shape()


def cut(base, tool):
    operation = BRepAlgoAPI_Cut(base, tool)
    operation.Build()
    if not operation.IsDone():
        raise RuntimeError("Boolean cut failed")
    return operation.Shape()


def x_cylinder(y: float, z: float, radius: float, length: float = 5.2):
    return BRepPrimAPI_MakeCylinder(
        gp_Ax2(gp_Pnt(-1.0, y, z), gp_Dir(1, 0, 0)),
        radius,
        length,
    ).Shape()


def rounded_plate():
    """A 3.2-mm X-thick plate with 3-mm Y-Z corner radii."""
    y0 = -PLATE_WIDTH_Y / 2
    z0 = PLATE_CENTER_Z - PLATE_HEIGHT_Z / 2
    # Orthogonal cores plus four cylinders produce the same rounded outline as
    # the OpenSCAD offset() construction, while remaining a native BRep solid.
    solid = BRepPrimAPI_MakeBox(
        gp_Pnt(0, y0 + CORNER_RADIUS, z0),
        PLATE_THICKNESS, PLATE_WIDTH_Y - 2 * CORNER_RADIUS, PLATE_HEIGHT_Z,
    ).Shape()
    solid = fuse(
        solid,
        BRepPrimAPI_MakeBox(
            gp_Pnt(0, y0, z0 + CORNER_RADIUS),
            PLATE_THICKNESS, PLATE_WIDTH_Y, PLATE_HEIGHT_Z - 2 * CORNER_RADIUS,
        ).Shape(),
    )
    for y in (y0 + CORNER_RADIUS, -y0 - CORNER_RADIUS):
        for z in (z0 + CORNER_RADIUS, z0 + PLATE_HEIGHT_Z - CORNER_RADIUS):
            solid = fuse(solid, x_cylinder(y, z, CORNER_RADIUS, PLATE_THICKNESS))
    return solid


def build():
    solid = rounded_plate()
    # Full connector/cable passage: Y = -8..8, Z = 21..43 mm.
    solid = cut(solid, BRepPrimAPI_MakeBox(gp_Pnt(-1, -8, 21), 5.2, 16.0, 22.0).Shape())
    for y, z in CHASSIS_HOLES:
        solid = cut(solid, x_cylinder(y, z, 1.7))
    for y, z in CAMERA_HOLES:
        solid = cut(solid, x_cylinder(y, z, 1.2))
    return solid


if __name__ == "__main__":
    writer = STEPControl_Writer()
    writer.Transfer(build(), STEPControl_AsIs)
    if writer.Write(str(OUT)) != 1:
        raise RuntimeError(f"Failed to write {OUT}")
    print(f"Wrote {OUT}")
