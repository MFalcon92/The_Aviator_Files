// ============================================================
//  THE AVIATOR — Drone Frame Mounting Plates
//  Pi 4 mounting plate + downward sonar centre mount
//  Bolts to Tarot FY690S centre plate (M3 hole pattern)
//  Print in PETG, 40% infill, 0.2mm layer height
// ============================================================

// ── Tarot FY690S centre plate reference ──────────────────────
// Centre plate is ~180x180mm with M3 holes on 45mm and 30mm grids
// We use the 45mm grid (4 bolts) for the Pi plate

// ── Parameters ───────────────────────────────────────────────
PLATE_W       = 94;     // Pi plate width
PLATE_L       = 68;     // Pi plate length
PLATE_T       = 3;      // plate thickness
MOUNT_HOLE_D  = 3.3;    // M3 holes for frame attachment
MOUNT_SPACING = 45;     // Tarot hole grid spacing
STANDOFF_H    = 6;      // standoff height above plate
STANDOFF_OD   = 7;      // standoff outer diameter
PI_HOLE_D     = 2.7;    // Pi4 M2.5 mounting holes
PI_HOLE_X     = 58;     // Pi hole separation X (long axis)
PI_HOLE_Y     = 49;     // Pi hole separation Y (short axis)
WIRE_SLOT_W   = 12;     // cable management slot width
WIRE_SLOT_L   = 20;
$fn           = 48;

// ── Sonar mount parameters ────────────────────────────────────
SONAR_BODY_W  = 45;     // HC-SR04 PCB width
SONAR_BODY_L  = 20;     // HC-SR04 PCB depth
SONAR_HOLE_SEP= 40;     // mounting hole separation
SONAR_HOLE_D  = 2.0;    // M2 holes
SONAR_PLATE_T = 3;      // sonar bracket thickness
SONAR_OFFSET  = 20;     // how far below main plate sonar sits
SONAR_RING_D  = 15;     // transducer ring diameter
SONAR_RING_SEP= 26;     // distance between two transducer centres

// ── Rounded rectangle helper ─────────────────────────────────
module rrect(w, l, t, r=4) {
    hull()
        for (x=[r, w-r]) for (y=[r, l-r])
            translate([x, y, 0]) cylinder(r=r, h=t);
}

// ── Pi mounting plate ─────────────────────────────────────────
module pi_plate() {
    difference() {
        rrect(PLATE_W, PLATE_L, PLATE_T, 4);

        // Frame attachment holes (4 corners, 45mm grid)
        for (x=[PLATE_W/2 - MOUNT_SPACING/2, PLATE_W/2 + MOUNT_SPACING/2])
        for (y=[PLATE_L/2 - MOUNT_SPACING/2, PLATE_L/2 + MOUNT_SPACING/2])
            translate([x, y, -1]) cylinder(d=MOUNT_HOLE_D, h=PLATE_T+2);

        // Pi 4 standoff holes
        for (x=[PLATE_W/2 - PI_HOLE_X/2, PLATE_W/2 + PI_HOLE_X/2])
        for (y=[PLATE_L/2 - PI_HOLE_Y/2, PLATE_L/2 + PI_HOLE_Y/2])
            translate([x, y, -1]) cylinder(d=PI_HOLE_D, h=PLATE_T+2);

        // Wire management slots
        translate([PLATE_W/2 - WIRE_SLOT_W/2, 4, -1])
            cube([WIRE_SLOT_W, WIRE_SLOT_L, PLATE_T+2]);
        translate([PLATE_W/2 - WIRE_SLOT_W/2, PLATE_L - WIRE_SLOT_L - 4, -1])
            cube([WIRE_SLOT_W, WIRE_SLOT_L, PLATE_T+2]);

        // Weight reduction — honeycomb-style cutouts
        for (xi=[0:1:2]) for (yi=[0:1:1])
            translate([12 + xi*24, 10 + yi*24, -1])
                cylinder(d=12, h=PLATE_T+2);
    }

    // Pi 4 standoffs
    for (x=[PLATE_W/2 - PI_HOLE_X/2, PLATE_W/2 + PI_HOLE_X/2])
    for (y=[PLATE_L/2 - PI_HOLE_Y/2, PLATE_L/2 + PI_HOLE_Y/2])
        translate([x, y, PLATE_T])
            difference() {
                cylinder(d=STANDOFF_OD, h=STANDOFF_H);
                translate([0,0,-1]) cylinder(d=PI_HOLE_D, h=STANDOFF_H+2);
            }
}

// ── Sonar centre mount ────────────────────────────────────────
// Mounts HC-SR04 facing straight down under the centre of the frame
// The claw mounts beside this — sonar beam must stay unobstructed
module sonar_mount() {
    difference() {
        union() {
            // base plate
            rrect(SONAR_BODY_W + 10, SONAR_BODY_L + 10, SONAR_PLATE_T, 3);
            // side walls to hold PCB
            translate([3, 3, SONAR_PLATE_T])
                difference() {
                    rrect(SONAR_BODY_W + 4, SONAR_BODY_L + 4, 6, 2);
                    translate([2, 2, -1])
                        rrect(SONAR_BODY_W, SONAR_BODY_L, 8, 2);
                }
        }

        // M2 PCB mounting holes
        for (x=[(SONAR_BODY_W + 10)/2 - SONAR_HOLE_SEP/2,
                (SONAR_BODY_W + 10)/2 + SONAR_HOLE_SEP/2])
            translate([x, (SONAR_BODY_L + 10)/2, -1])
                cylinder(d=SONAR_HOLE_D, h=SONAR_PLATE_T+8);

        // Transducer windows (the two round sensors must be unobstructed)
        for (ox=[-SONAR_RING_SEP/2, SONAR_RING_SEP/2])
            translate([(SONAR_BODY_W + 10)/2 + ox,
                       (SONAR_BODY_L + 10)/2, -1])
                cylinder(d=SONAR_RING_D, h=SONAR_PLATE_T+2);

        // Frame attachment holes (M3, 30mm spacing)
        for (x=[(SONAR_BODY_W+10)/2 - 15, (SONAR_BODY_W+10)/2 + 15])
        for (y=[4, SONAR_BODY_L + 6])
            translate([x, y, -1]) cylinder(d=MOUNT_HOLE_D, h=SONAR_PLATE_T+2);
    }
}

// ── Assembly preview ──────────────────────────────────────────
// Pi mounting plate (top of drone)
pi_plate();

// Sonar mount (shown offset below for preview)
translate([0, PLATE_L + 20, 0])
    sonar_mount();

// ── Export notes ──────────────────────────────────────────────
// Export pi_plate() alone as "pi_mounting_plate.stl"
// Export sonar_mount() alone as "sonar_centre_mount.stl"
