// ============================================================
//  THE AVIATOR — Forward Camera Mount
//  Clamps to Tarot FY690S front arm (16mm OD tube)
//  Pi Camera v2 faces forward at 7 degrees downward tilt
//  Print in PETG, 60% infill, 0.2mm layer height
// ============================================================

ARM_OD        = 16.0;
ARM_CLAMP_GAP = 0.4;
CLAMP_W       = 28;
CLAMP_WALL    = 4;
BOLT_D        = 3.2;
BOLT_HEAD_D   = 6.0;
CAM_W         = 25;
CAM_H         = 24;
CAM_MOUNT_SEP = 21;
CAM_HOLE_D    = 2.0;
CAM_PLATE_T   = 3.0;
TILT_DEG      = 7;
RIBBON_SLOT_W = 18;
RIBBON_SLOT_T = 2.0;
$fn           = 64;

module clamp_lower() {
    r = ARM_OD/2 + ARM_CLAMP_GAP + CLAMP_WALL;
    difference() {
        translate([-r, -r, 0]) cube([r*2, r, CLAMP_W]);
        translate([0, 0, -1]) cylinder(r=ARM_OD/2 + ARM_CLAMP_GAP, h=CLAMP_W+2);
        for (x=[-r*0.55, r*0.55])
        for (z=[CLAMP_W*0.25, CLAMP_W*0.75]) {
            translate([x, -CLAMP_WALL/2, z])
                rotate([90,0,0]) cylinder(d=BOLT_D, h=CLAMP_WALL+2);
        }
    }
}

module clamp_upper() {
    r = ARM_OD/2 + ARM_CLAMP_GAP + CLAMP_WALL;
    difference() {
        translate([-r, 0, 0]) cube([r*2, r, CLAMP_W]);
        translate([0, 0, -1]) cylinder(r=ARM_OD/2 + ARM_CLAMP_GAP, h=CLAMP_W+2);
        for (x=[-r*0.55, r*0.55])
        for (z=[CLAMP_W*0.25, CLAMP_W*0.75]) {
            translate([x, CLAMP_WALL/2, z])
                rotate([90,0,0]) {
                    cylinder(d=BOLT_D, h=CLAMP_WALL+2);
                    translate([0,0,-1]) cylinder(d=BOLT_HEAD_D, h=CLAMP_WALL*0.6+1);
                }
        }
    }
}

module camera_plate() {
    difference() {
        translate([-CAM_W/2 - 3, 0, 0])
            cube([CAM_W + 6, CAM_PLATE_T, CAM_H + 6]);
        translate([-CAM_W/2, -1, 3])
            cube([CAM_W, CAM_PLATE_T+2, CAM_H]);
        for (x=[-CAM_MOUNT_SEP/2, CAM_MOUNT_SEP/2])
            translate([x, -1, CAM_H/2 + 3])
                rotate([-90,0,0]) cylinder(d=CAM_HOLE_D, h=CAM_PLATE_T+2);
        translate([-RIBBON_SLOT_W/2, -1, CAM_H + 3])
            cube([RIBBON_SLOT_W, CAM_PLATE_T+2, 4]);
    }
}

module neck() {
    r = ARM_OD/2 + ARM_CLAMP_GAP + CLAMP_WALL;
    hull() {
        translate([-6, -r, 0]) cube([12, 1, CLAMP_W]);
        translate([-6, -r - 18, CLAMP_W*0.2])
            cube([12, 1, CLAMP_W*0.6]);
    }
}

// Lower clamp
clamp_lower();
// Neck
neck();
// Camera plate (tilted)
translate([0, -(ARM_OD/2 + ARM_CLAMP_GAP + CLAMP_WALL + 18), CLAMP_W/2])
    rotate([TILT_DEG, 0, 0])
        camera_plate();

// Upper clamp (shown offset for printing — print separately)
translate([0, ARM_OD + ARM_CLAMP_GAP*2 + CLAMP_WALL*2 + 8, 0])
    clamp_upper();
