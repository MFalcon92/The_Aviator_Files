// ============================================================
//  THE AVIATOR — Claw Mechanism
//  File   : claw_mechanism.scad
//  Author : The Aviator Project
//  License: MIT
//
//  Description:
//    3-finger downward-facing claw driven by an Acxiico N20
//    gear motor via a simple rack-and-pinion or linkage.
//    Fingers splay outward when open and close inward to grab.
//
//  Print settings:
//    Material  : PETG
//    Infill    : 50%
//    Layer h   : 0.15mm
//    Supports  : Yes (finger joint overhangs)
//
//  To export STL:
//    Open in OpenSCAD → F6 (render) → File → Export → STL
//    Export each module separately using the render() calls
//    at the bottom of this file.
// ============================================================

// ── Parameters ───────────────────────────────────────────────
$fn = 64;   // circle resolution — higher = smoother, slower

// Body
BODY_DIAMETER   = 50;    // mm — outer diameter of central hub
BODY_HEIGHT     = 20;    // mm — height of central hub
WALL            = 3;     // mm — wall thickness throughout

// Motor shaft hole (N20 D-shaft)
SHAFT_DIAMETER  = 3.2;   // mm — 3mm D-shaft with clearance
SHAFT_FLAT      = 2.7;   // mm — D-shaft flat chord width
SHAFT_DEPTH     = 12;    // mm — how deep shaft inserts

// Motor body recess (N20 body is ~12mm × 10mm)
MOTOR_W         = 12.5;  // mm
MOTOR_H         = 10.5;  // mm
MOTOR_DEPTH     = 8;     // mm

// Fingers
FINGER_COUNT    = 3;
FINGER_W        = 8;     // mm — finger width
FINGER_T        = 4;     // mm — finger thickness
FINGER_L        = 40;    // mm — finger length (from pivot to tip)
FINGER_SPREAD   = 20;    // mm — radial offset of pivot from body centre
FINGER_OPEN_ANGLE  = 35; // degrees — open position angle from vertical
FINGER_CLOSE_ANGLE = 5;  // degrees — closed position angle from vertical

// Pivot pin hole
PIVOT_D         = 3.2;   // mm — M3 bolt pivot

// Grip pad recess on fingertip
PAD_W           = 6;     // mm
PAD_L           = 10;    // mm
PAD_DEPTH       = 1.5;   // mm — recess for gluing rubber pad


// ── D-shaft profile (N20 motor shaft) ────────────────────────
module d_shaft_hole(depth) {
    cylinder(h = depth, d = SHAFT_DIAMETER);
    // Flat on the D
    translate([-SHAFT_DIAMETER/2, SHAFT_FLAT/2 - SHAFT_DIAMETER, 0])
        cube([SHAFT_DIAMETER, SHAFT_DIAMETER, depth]);
}


// ── Central hub ───────────────────────────────────────────────
//    Mounts to drone underside, houses motor, carries finger pivots
module claw_body() {
    difference() {
        union() {
            // Main hub cylinder
            cylinder(h = BODY_HEIGHT, d = BODY_DIAMETER);

            // Three pivot bosses equally spaced around the hub
            for (i = [0 : FINGER_COUNT - 1]) {
                angle = i * (360 / FINGER_COUNT);
                rotate([0, 0, angle])
                translate([FINGER_SPREAD, 0, 0])
                    cylinder(h = BODY_HEIGHT, d = FINGER_W + WALL * 2);
            }
        }

        // Motor body recess (top face, centred)
        translate([-MOTOR_W/2, -MOTOR_H/2, BODY_HEIGHT - MOTOR_DEPTH])
            cube([MOTOR_W, MOTOR_H, MOTOR_DEPTH + 0.1]);

        // Motor shaft hole (through centre, from top)
        translate([0, 0, BODY_HEIGHT - SHAFT_DEPTH])
            d_shaft_hole(SHAFT_DEPTH + 0.1);

        // M4 drone mounting holes — 30mm bolt circle, 4 holes
        for (i = [0:3]) {
            rotate([0, 0, i * 90 + 45])
            translate([15, 0, -0.1])
                cylinder(h = BODY_HEIGHT + 0.2, d = 4.3);
        }

        // Pivot pin holes through each boss
        for (i = [0 : FINGER_COUNT - 1]) {
            angle = i * (360 / FINGER_COUNT);
            rotate([0, 0, angle])
            translate([FINGER_SPREAD, 0, BODY_HEIGHT / 2])
                rotate([90, 0, 0])
                    cylinder(h = FINGER_W + WALL * 2 + 2, d = PIVOT_D,
                             center = true);
        }
    }
}


// ── Single finger ─────────────────────────────────────────────
//    Print 3 copies. Pivots on M3 bolt through hub boss.
//    Shown in OPEN position — rotate FINGER_OPEN_ANGLE outward.
module claw_finger() {
    difference() {
        union() {
            // Main finger arm
            translate([-FINGER_W/2, 0, 0])
                cube([FINGER_W, FINGER_L, FINGER_T]);

            // Pivot ear at top of finger
            translate([0, 0, 0])
                cylinder(h = FINGER_T, d = FINGER_W, center = false);
        }

        // Pivot hole
        translate([0, 0, -0.1])
            cylinder(h = FINGER_T + 0.2, d = PIVOT_D);

        // Grip pad recess at fingertip (bottom face)
        translate([-PAD_W/2, FINGER_L - PAD_L, -0.1])
            cube([PAD_W, PAD_L, PAD_DEPTH + 0.1]);
    }
}


// ── Motor mount plate (separate part, bonds to hub top) ───────
module motor_mount() {
    difference() {
        cylinder(h = 4, d = BODY_DIAMETER);

        // Motor body slot
        translate([-MOTOR_W/2, -MOTOR_H/2, -0.1])
            cube([MOTOR_W, MOTOR_H, 4.2]);

        // Shaft clearance
        cylinder(h = 4.2, d = SHAFT_DIAMETER + 1);

        // Matching mounting holes
        for (i = [0:3]) {
            rotate([0, 0, i * 90 + 45])
            translate([15, 0, -0.1])
                cylinder(h = 4.2, d = 4.3);
        }
    }
}


// ── Render / export targets ───────────────────────────────────
//    Comment/uncomment each section to export individual STLs.

// --- BODY (export as claw_body.stl) ---
claw_body();

// --- FINGER — export as claw_finger.stl, print x3 ---
// Shown in open position for clarity
// translate([40, 0, 0])
//     rotate([0, 0, 0])
//         claw_finger();

// --- MOTOR MOUNT — export as claw_motor_mount.stl ---
// translate([0, 60, 0])
//     motor_mount();

// ── Assembly preview (all parts together) ────────────────────
//    Uncomment to see full assembly
// claw_body();
// for (i = [0 : FINGER_COUNT - 1]) {
//     angle = i * (360 / FINGER_COUNT);
//     rotate([0, 0, angle])
//     translate([FINGER_SPREAD, 0, BODY_HEIGHT / 2])
//     rotate([0, FINGER_OPEN_ANGLE, 0])
//     translate([0, -FINGER_T/2, 0])
//         claw_finger();
// }
