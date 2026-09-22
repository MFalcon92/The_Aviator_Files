// ============================================================
//  THE AVIATOR — Drone Mounting Plates
//  File   : drone_frame_mounts.scad
//  Author : The Aviator Project
//  License: MIT
//
//  Description:
//    Custom mounting plates for the Tarot FY690S frame.
//    Contains three printable parts:
//
//    1. pi_mount       — Raspberry Pi 4 top plate with M2.5 standoffs
//    2. sonar_mount    — HC-SR04 centre-bottom bracket, beam down
//    3. sensor_bridge  — Bridges sonar and Pi sensor board
//
//  Print settings:
//    Material  : PETG
//    Infill    : 40%
//    Layer h   : 0.2mm
//    Supports  : No
//
//  Hardware:
//    4× M2.5×6  screws + brass inserts — Pi mounting
//    2× M3×10   screws + nuts          — sonar bracket to frame
//    1× M3×6    screw                  — sensor board bridge
// ============================================================

$fn = 48;

// ── Raspberry Pi 4 mounting plate ────────────────────────────
//    Pi PCB: 85mm × 56mm
//    Hole pattern: 58mm × 49mm, M2.5, from corner (3.5mm in each axis)
PI_W            = 85;
PI_H            = 56;
PLATE_W         = 95;    // mm — plate slightly larger than Pi
PLATE_H         = 66;    // mm
PLATE_T         = 2.5;   // mm — plate thickness
STANDOFF_H      = 5;     // mm — standoff height (clears Pi components)
STANDOFF_OD     = 6;     // mm
STANDOFF_HOLE   = 2.7;   // mm — M2.5 clearance
CORNER_R        = 4;     // mm

// Pi hole positions (from plate centre, matching Pi PCB layout)
PI_HOLES = [
    [-58/2 + 3.5 - PI_W/2 + PLATE_W/2 - (PLATE_W-PI_W)/2,
      49/2 - 3.5 - PI_H/2 + PLATE_H/2 - (PLATE_H-PI_H)/2],
    [ 58/2 + 3.5 - PI_W/2 + PLATE_W/2 - (PLATE_W-PI_W)/2 - 58 + 55,
      49/2 - 3.5 - PI_H/2 + PLATE_H/2 - (PLATE_H-PI_H)/2],
    [-58/2 + 3.5 - PI_W/2 + PLATE_W/2 - (PLATE_W-PI_W)/2,
     -49/2 - 3.5 + PI_H/2 - PLATE_H/2 + (PLATE_H-PI_H)/2 + 49 - 6.5],
    [ 58/2 + 3.5 - PI_W/2 + PLATE_W/2 - (PLATE_W-PI_W)/2 - 58 + 55,
     -49/2 - 3.5 + PI_H/2 - PLATE_H/2 + (PLATE_H-PI_H)/2 + 49 - 6.5],
];

// Simplified hole positions relative to plate centre
// Pi 4 hole pattern: 58mm × 49mm from top-left corner at (3.5, 3.5)
PI_HOLE_POS = [
    [-23.5,  17.5],
    [ 23.5,  17.5],
    [-23.5, -13.5],
    [ 23.5, -13.5],
];

// Frame mounting — M3 holes on 30.5mm spacing (Tarot centre plate pattern)
FRAME_HOLE_D    = 3.3;
FRAME_HOLE_SPAN = 30.5;

module pi_mount() {
    difference() {
        // Rounded plate
        hull() {
            for (x = [CORNER_R - PLATE_W/2, PLATE_W/2 - CORNER_R])
            for (y = [CORNER_R - PLATE_H/2, PLATE_H/2 - CORNER_R])
                translate([x, y, 0])
                    cylinder(h = PLATE_T, r = CORNER_R);
        }

        // Frame bolt holes (pass-through)
        for (x = [-FRAME_HOLE_SPAN/2, FRAME_HOLE_SPAN/2])
        for (y = [-FRAME_HOLE_SPAN/2, FRAME_HOLE_SPAN/2])
            translate([x, y, -0.1])
                cylinder(h = PLATE_T + 0.2, d = FRAME_HOLE_D);

        // Cutout to reduce weight / improve airflow
        translate([0, 0, -0.1])
            cylinder(h = PLATE_T + 0.2, d = 20);
    }

    // Pi standoffs — M2.5 boss at each Pi hole
    for (p = PI_HOLE_POS)
        translate([p[0], p[1], PLATE_T])
            difference() {
                cylinder(h = STANDOFF_H, d = STANDOFF_OD);
                cylinder(h = STANDOFF_H + 0.1, d = STANDOFF_HOLE);
            }
}


// ── HC-SR04 Sonar mount ───────────────────────────────────────
//    Holds sonar pointing STRAIGHT DOWN, centred under frame.
//    Mounts to drone underside centre plate with M3 bolts.
//    Claw mounts beside it — sonar beam must be unobstructed.

SONAR_W         = 45;    // mm — HC-SR04 PCB width
SONAR_H         = 20;    // mm — HC-SR04 PCB height
SONAR_WALL      = 2;     // mm
SONAR_CLIP_H    = 8;     // mm — clip height to hold sonar PCB
SONAR_HOLE_D    = 3.3;   // mm — M3 mounting bolt
SONAR_HOLE_SPAN = 30;    // mm — bolt spacing

// Sonar transducer positions (HC-SR04 has two 16mm domes, 26mm apart)
SONAR_DOME_D    = 17;    // mm — transducer hole diameter
SONAR_DOME_SEP  = 26;    // mm — centre-to-centre

module sonar_mount() {
    difference() {
        union() {
            // Base plate
            hull() {
                for (x = [-(SONAR_W/2 + SONAR_WALL),
                            SONAR_W/2 + SONAR_WALL])
                for (y = [-(SONAR_H/2 + SONAR_WALL),
                            SONAR_H/2 + SONAR_WALL])
                    translate([x, y, 0])
                        cylinder(h = PLATE_T, r = 2);
            }

            // PCB clip walls — two sides (left and right of sonar)
            for (side = [-1, 1])
                translate([side * (SONAR_W/2 + SONAR_WALL - SONAR_WALL),
                           0, PLATE_T])
                    cube([SONAR_WALL * 2, SONAR_H, SONAR_CLIP_H],
                         center = true);

            // Clip lip at top to retain sonar PCB
            for (side = [-1, 1])
                translate([side * (SONAR_W/2 + SONAR_WALL),
                           0, PLATE_T + SONAR_CLIP_H - 1.5])
                    cube([2, SONAR_H, 2], center = true);
        }

        // Sonar transducer holes (pass-through for sound waves downward)
        for (xoff = [-SONAR_DOME_SEP/2, SONAR_DOME_SEP/2])
            translate([xoff, 0, -0.1])
                cylinder(h = PLATE_T + 0.2, d = SONAR_DOME_D);

        // Frame mounting bolt holes
        for (x = [-SONAR_HOLE_SPAN/2, SONAR_HOLE_SPAN/2])
            translate([x, 0, -0.1])
                cylinder(h = PLATE_T + 0.2, d = SONAR_HOLE_D);
    }
}


// ── Render / export targets ───────────────────────────────────

// Export as pi_mount.stl
pi_mount();

// Export as sonar_mount.stl — uncomment and re-export
// translate([120, 0, 0])
//     sonar_mount();

// Assembly preview
// pi_mount();
// translate([0, -80, 0])
//     sonar_mount();
