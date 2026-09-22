// ============================================================
//  THE AVIATOR — Claw Mechanism
//  Acxiico N20 gear motor driven, 3-finger downward grab
//  Print in PETG, 50% infill, 0.15mm layer height
// ============================================================

// ── Parameters (edit these to tune your claw) ──────────────
BODY_D        = 48;     // body cylinder diameter (mm)
BODY_H        = 22;     // body cylinder height (mm)
MOTOR_D       = 10.5;   // N20 motor body diameter
MOTOR_L       = 24;     // N20 motor body length
SHAFT_D       = 3.0;    // N20 D-shaft diameter
FINGER_W      = 8;      // finger width
FINGER_T      = 4;      // finger thickness
FINGER_L      = 32;     // finger length (reach below body)
FINGER_TIP_W  = 14;     // tip spread width (contact pad width)
FINGER_TIP_H  = 6;      // tip height
PAD_T         = 1.5;    // rubber pad recess depth
MOUNT_HOLE_D  = 3.2;    // M3 mounting holes through body
MOUNT_RING_D  = 56;     // bolt circle diameter for frame mount
$fn           = 64;

// ── Convenience ─────────────────────────────────────────────
module rounded_box(x, y, z, r=2) {
    hull() {
        for (dx=[-x/2+r, x/2-r])
        for (dy=[-y/2+r, y/2-r])
            translate([dx, dy, 0]) cylinder(r=r, h=z);
    }
}

// ── Motor pocket (inside body) ───────────────────────────────
module motor_pocket() {
    // cylindrical motor body
    translate([0, 0, BODY_H - MOTOR_L - 2])
        cylinder(d=MOTOR_D + 0.4, h=MOTOR_L + 3);
    // D-shaft slot through bottom
    hull() {
        cylinder(d=SHAFT_D + 0.3, h=BODY_H);
        translate([SHAFT_D * 0.2, 0, 0])
            cylinder(d=SHAFT_D + 0.3, h=BODY_H);
    }
}

// ── Single finger ────────────────────────────────────────────
module finger() {
    difference() {
        union() {
            // main finger shaft
            rounded_box(FINGER_W, FINGER_T, FINGER_L, r=1.5);
            // angled tip / contact pad
            translate([0, -FINGER_TIP_W/2 + FINGER_T/2, -FINGER_TIP_H])
                rounded_box(FINGER_W, FINGER_TIP_W, FINGER_TIP_H + 1, r=2);
        }
        // rubber pad recess on inner face of tip
        translate([0, -FINGER_TIP_W/2 + FINGER_T/2 - PAD_T, -FINGER_TIP_H + 1])
            rounded_box(FINGER_W - 2, FINGER_TIP_W/2, FINGER_TIP_H, r=1);
        // pivot pin hole
        translate([0, 0, FINGER_L - 4])
            rotate([90, 0, 0]) cylinder(d=2.5, h=FINGER_T + 4, center=true);
    }
}

// ── Main body ─────────────────────────────────────────────────
module body() {
    difference() {
        // outer cylinder
        cylinder(d=BODY_D, h=BODY_H);

        // motor pocket
        motor_pocket();

        // finger pivot slots (3 × 120°)
        for (a=[0, 120, 240]) rotate([0, 0, a])
            translate([BODY_D/2 - 5, 0, 4])
                rotate([90, 0, 0])
                    cylinder(d=2.8, h=10, center=true);

        // M3 frame mounting holes (4 × 90°)
        for (a=[0, 90, 180, 270]) rotate([0, 0, a])
            translate([MOUNT_RING_D/2, 0, BODY_H/2])
                cylinder(d=MOUNT_HOLE_D, h=BODY_H + 2, center=true);

        // wire channel
        translate([0, BODY_D/4, -1])
            cylinder(d=5, h=6);

        // ventilation / weight reduction
        for (a=[60, 180, 300]) rotate([0, 0, a])
            translate([BODY_D/2 - 10, 0, BODY_H/2])
                cylinder(d=8, h=BODY_H + 2, center=true);
    }
}

// ── Finger link arm (connects motor cam to finger pivot) ─────
module link_arm() {
    difference() {
        rounded_box(18, 5, 3.5, r=1.5);
        // motor cam slot
        translate([-6, 0, 0]) cylinder(d=2.5, h=5, center=true);
        // finger pivot hole
        translate([6, 0, 0])  cylinder(d=2.5, h=5, center=true);
    }
}

// ── Motor cam disc (attaches to N20 shaft) ───────────────────
module motor_cam() {
    difference() {
        cylinder(d=16, h=5);
        // D-shaft hole
        translate([0, 0, -1]) {
            cylinder(d=SHAFT_D, h=7);
            translate([SHAFT_D * 0.3, -SHAFT_D/2, 0])
                cube([SHAFT_D, SHAFT_D, 7]);
        }
        // link arm pin holes (3 × 120°, offset 5mm from centre)
        for (a=[0, 120, 240]) rotate([0, 0, a])
            translate([5, 0, 0]) cylinder(d=2.5, h=7, center=true);
    }
}

// ── Assembly (exploded for clarity — comment out offsets to nest) ──
// Body
body();

// Three fingers placed 120° apart, pivoting from body edge
for (a=[0, 120, 240]) {
    rotate([0, 0, a])
    translate([BODY_D/2 - 5, 0, 4])
        rotate([0, 90, 0])
            finger();
}

// Motor cam (shown above body — sits on N20 shaft inside body)
translate([0, 0, BODY_H + 5]) motor_cam();

// Three link arms
for (a=[0, 120, 240]) {
    rotate([0, 0, a])
    translate([8, 0, BODY_H + 5])
        link_arm();
}
