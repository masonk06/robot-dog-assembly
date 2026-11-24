// Luca P2S camera-to-chassis adapter.  Units: mm.
//
// Purpose: bridge the two existing chassis mast holes (M3, 34 mm pitch) to
// the four-hole board pattern of a Raspberry Pi Camera Module 3 (IMX708;
// M2, 21 x 12.5 mm). This part deliberately does not alter the chassis.
//
// Coordinate convention inside adapter() matches the P2S CAD: X points
// fore/aft, Y is lateral, and Z is vertical. The final transform below puts
// the broad face flat on the print bed. The installed hole axes are along X.

$fn = 48;

// --- Verified-from-CAD interface dimensions ---
chassis_hole_pitch_y = 34;       // centres at Y = +/-17
chassis_hole_z = 32;
chassis_screw_clearance = 3.4;   // M3 clearance

camera_hole_pitch_y = 21;        // centres at Y = +/-10.5
camera_hole_pitch_z = 12.5;      // centres at Z = 22 and 34.5
camera_screw_clearance = 2.4;    // M2 clearance; do not force a self-tapper
camera_hole_z = 28.25;

// Rear FFC connector clearance, based on the matching opening in the existing
// P2S Camera_Insert. The opening lets the camera PCB sit on the adapter's
// perimeter rails instead of bearing on its ribbon connector.
connector_relief_width_y = 16;
connector_relief_height_z = 22;
connector_relief_z = 32;

// --- Print geometry ---
plate_thickness = 3.2;
plate_width_y = 46;
// The top edge ends 1.3 mm beyond the upper M2-hole edge. This removes the
// camera-side obstruction while retaining a printable screw-hole rim.
plate_height_z = 21.5;
plate_center_z = 26.5;
corner_radius = 3;
edge_margin = 3;

module rounded_plate() {
    // Minkowski keeps material around the outer chassis holes while softening
    // the corners; $fn is intentionally modest for an easy-to-slice STL.
    linear_extrude(height = plate_thickness, center = true)
        offset(r = corner_radius)
            // This local X dimension becomes global Z after the rotation in
            // adapter(); local Y remains global Y.
            square([plate_height_z - 2 * corner_radius,
                    plate_width_y - 2 * corner_radius], center = true);
}

module x_hole(diameter, y, z) {
    // Rotate the cylinder at its local origin, then place its X-axis bore in
    // the assembly's Y-Z plane. Translating before rotating would incorrectly
    // rotate the requested Y-Z coordinates as well.
    translate([0, y, z])
        rotate([0, 90, 0])
            cylinder(h = plate_thickness + 2, d = diameter, center = true);
}

module adapter() {
    difference() {
        // OpenSCAD's extrude is along Z.  Rotate to make the plate lie in Y-Z,
        // putting every fastener axis along X as on the existing parts.
        // Place the plate at the camera-pattern centre in chassis coordinates.
        // The holes below are already expressed in those same coordinates.
        translate([0, 0, plate_center_z])
            rotate([0, 90, 0]) rounded_plate();

        // Through-window for the rear camera connector and its cable. This
        // leaves 3 mm side rails and a 5.25 mm lower support ledge.
        translate([0, 0, connector_relief_z])
            cube([plate_thickness + 2,
                  connector_relief_width_y,
                  connector_relief_height_z], center = true);

        // Existing chassis mast interface: M3 clearance, two holes.
        for (y = [-chassis_hole_pitch_y / 2, chassis_hole_pitch_y / 2])
            x_hole(chassis_screw_clearance, y, chassis_hole_z);

        // Raspberry Pi Camera Module 3 / IMX708 interface: M2 clearance.
        for (y = [-camera_hole_pitch_y / 2, camera_hole_pitch_y / 2])
            for (z = [camera_hole_z - camera_hole_pitch_z / 2,
                      camera_hole_z + camera_hole_pitch_z / 2])
                x_hole(camera_screw_clearance, y, z);
    }
}

// Exported orientation: broad face on the print bed, with the thin dimension
// along print Z. The adapter() module itself remains in chassis coordinates.
translate([camera_hole_z, 0, plate_thickness / 2])
    rotate([0, -90, 0]) adapter();
