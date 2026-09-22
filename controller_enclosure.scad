// ============================================================
//  THE AVIATOR — Handheld Controller Enclosure (Simple 5-Button)
//
//  Buttons (no joystick):
//    ARM/LAND  — top centre
//    GRAB      — bottom left
//    RELEASE   — bottom right
//    LASER     — right thumb, centre
//    POWER OFF — top left corner (recessed, hard to hit by accident)
//
//  Print in PETG, 40% infill, 0.2mm layer height
//  Two parts: top shell + battery lid
//  Export each separately for printing
// ============================================================

// ── Outer dimensions ─────────────────────────────────────────
W    = 130;   // width  (left-right)
H    = 95;    // height (face, top-bottom)
D    = 44;    // depth  (front to back, thickness you hold)
WALL = 2.8;   // shell wall thickness
R    = 6;     // outer corner radius
$fn  = 48;

// ── Hole sizes ────────────────────────────────────────────────
BTN_D        = 16;    // standard panel-mount button hole
LASER_PORT_D = 8;     // laser beam exit port on right edge
USB_W        = 10;    // USB-A slot (for flashing Arduino)
USB_H        = 4.5;
SCREW_D      = 3.2;   // M3 shell joining screws
BOSS_D       = 6.5;   // screw boss outer diameter

// ── Button positions on front face (x from left, y from bottom) ──
//
//  Layout:
//
//   [PWR OFF]              [ARM/LAND]
//
//
//         (smooth face — no joystick)
//                                      [LASER]
//
//   [GRAB]                 [RELEASE]
//
PWR_X  = 18;    PWR_Y  = H - 16;   // top left  — recessed, intentionally awkward
ARM_X  = W/2;   ARM_Y  = H - 16;   // top centre — most prominent
LSR_X  = W-16;  LSR_Y  = H/2;      // right side — right thumb reach
GRB_X  = 22;    GRB_Y  = 16;       // bottom left
REL_X  = W-22;  REL_Y  = 16;       // bottom right

// ── Helpers ───────────────────────────────────────────────────
module rbox(w, h, d, r=R) {
    hull()
        for (x=[r, w-r]) for (y=[r, h-r])
            translate([x, y, 0]) cylinder(r=r, h=d);
}

module btn_hole(x, y) {
    translate([x, y, -1]) cylinder(d=BTN_D, h=WALL+2);
}

// ── Label slot (shallow recess below each button for a sticker) ──
module label_slot(x, y) {
    translate([x - 10, y - BTN_D/2 - 7, -0.6])
        cube([20, 5, 1.2]);
}

// ── Main shell ────────────────────────────────────────────────
module top_shell() {
    difference() {
        // outer body
        rbox(W, H, D, R);

        // hollow interior
        translate([WALL, WALL, WALL])
            rbox(W-WALL*2, H-WALL*2, D-WALL+1, R-WALL);

        // ── front face button holes ──
        btn_hole(PWR_X, PWR_Y);
        btn_hole(ARM_X, ARM_Y);
        btn_hole(LSR_X, LSR_Y);
        btn_hole(GRB_X, GRB_Y);
        btn_hole(REL_X, REL_Y);

        // ── label slots ──
        label_slot(PWR_X, PWR_Y);
        label_slot(ARM_X, ARM_Y);
        label_slot(LSR_X, LSR_Y);
        label_slot(GRB_X, GRB_Y);
        label_slot(REL_X, REL_Y);

        // ── laser exit port on right side ──
        translate([W+1, LSR_Y, D/2])
            rotate([0,-90,0]) cylinder(d=LASER_PORT_D, h=WALL+2);

        // ── USB slot on left side for flashing Arduino ──
        translate([-1, H*0.25, D/2 - USB_W/2])
            cube([WALL+2, USB_H, USB_W]);

        // ── battery door slot on rear face ──
        translate([W*0.2, -1, WALL])
            cube([W*0.6, WALL+2, D*0.38]);

        // ── grip texture channels on sides (ergonomic) ──
        for (z=[D*0.3, D*0.5, D*0.7])
            translate([-1, H*0.2, z])
                cube([WALL+2, H*0.6, 2]);
        for (z=[D*0.3, D*0.5, D*0.7])
            translate([W-WALL-1, H*0.2, z])
                cube([WALL+2, H*0.6, 2]);
    }

    // ── M3 boss posts at 4 corners (shells bolt together) ──
    inset = WALL + BOSS_D * 0.5;
    for (x=[inset, W-inset]) for (y=[inset, H-inset])
        translate([x, y, WALL])
            difference() {
                cylinder(d=BOSS_D, h=8);
                translate([0,0,-1]) cylinder(d=SCREW_D, h=10);
            }

    // ── Arduino Nano PCB standoffs (18x43mm footprint) ──
    // Centred horizontally, in the middle-lower half of shell
    for (x=[W/2-9, W/2+9]) for (y=[H*0.2, H*0.2+43])
        translate([x, y, WALL])
            difference() {
                cylinder(d=5, h=5);
                translate([0,0,-1]) cylinder(d=2.2, h=7);
            }

    // ── nRF24L01 module socket standoffs (15x29mm) ──
    // Positioned above Arduino in upper-centre of shell
    for (x=[W/2-7.5, W/2+7.5]) for (y=[H*0.68, H*0.68+29])
        translate([x, y, WALL])
            difference() {
                cylinder(d=4, h=4);
                translate([0,0,-1]) cylinder(d=2.0, h=6);
            }
}

// ── Battery lid ───────────────────────────────────────────────
module battery_lid() {
    lw = W*0.6 - WALL*2;
    lh = D*0.38 - WALL;
    translate([W*0.2 + WALL, 0, 0]) {
        difference() {
            cube([lw, WALL*1.6, lh + WALL]);
            // hollow slot that slides into shell
            translate([WALL, -1, WALL])
                cube([lw - WALL*2, WALL*2+2, lh]);
            // finger pull notch
            translate([lw/2, -1, lh/2])
                rotate([-90,0,0])
                    cylinder(d=10, h=WALL*2+2);
        }
    }
}

// ── Preview both parts ────────────────────────────────────────
top_shell();
translate([0, -(D*0.42 + 14), 0]) battery_lid();

// ── To export individual STLs: ────────────────────────────────
// Comment out the lines above and uncomment one at a time:
// top_shell();
// battery_lid();
