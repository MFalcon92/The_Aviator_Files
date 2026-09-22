# cad/controller_enclosure

Handheld housing for the Arduino Nano, nRF24L01 radio, 5 buttons, laser module, and 9V battery. No joystick.

## Button Layout

```
┌─────────────────────────────────────────┐
│  [PWR OFF]              [ARM/LAND]      │  ← top row
│                                         │
│                                         │
│                              [LASER] →  │  ← right side, thumb reach
│                                         │
│                                         │
│  [GRAB]                 [RELEASE]       │  ← bottom row
│                           [Laser port]──►
│                                         │
│  ══════════════════════════════════     │
│  Battery bay (9V) — rear slide door     │
└─────────────────────────────────────────┘
```

**Why this layout:**
- **POWER OFF** is top left — physically awkward to reach mid-flight, so you won't hit it by accident
- **ARM/LAND** is top centre — prominent, the first and last button you press every flight
- **LASER** is on the right side at thumb height — you hold it while aiming, so it needs to be comfortable to hold down
- **GRAB** and **RELEASE** are at the bottom where your fingers naturally rest — the two most-used buttons during a mission

## Design Requirements

- Fits Arduino Nano + nRF24L01 module internally with PCB standoffs
- 9V battery bay accessible from rear without tools (sliding door)
- 5 button holes, 16mm diameter, panel-mount style
- Laser exit port on right side edge (8mm round hole)
- USB slot on left side edge so you can flash the Arduino without opening the enclosure
- nRF24L01 antenna must not be blocked by any metal components
- Grip texture channels on both side walls for comfortable hold
- Comfortable two-hand grip — 130mm wide, 95mm tall, 44mm deep

## Actual Dimensions (from controller_enclosure.scad)

| Dimension | Value |
|---|---|
| Width | 130mm |
| Height | 95mm |
| Depth | 44mm |
| Wall thickness | 2.8mm |
| Outer corner radius | 6mm |
| Button hole diameter | 16mm |
| Laser exit port diameter | 8mm |
| USB slot | 10mm × 4.5mm |

## Button Positions (x from left, y from bottom of front face)

| Button | X | Y |
|---|---|---|
| POWER OFF | 18mm | 79mm |
| ARM/LAND | 65mm (centre) | 79mm |
| LASER | 114mm | 47mm (right side reach) |
| GRAB | 22mm | 16mm |
| RELEASE | 108mm | 16mm |

## Internal Component Positions

- **Arduino Nano** — centre of shell, lower half. PCB standoffs at 18×43mm footprint
- **nRF24L01 module** — centre of shell, upper half. Standoffs at 15×29mm footprint
- **9V battery** — behind sliding rear door, lower third of enclosure depth

## Files in This Folder

| Filename | Format | Description |
|---|---|---|
| `controller_enclosure.scad` | OpenSCAD | Full parametric design — edit dimensions at top of file |

## Exporting STLs from OpenSCAD

Open `controller_enclosure.scad` in OpenSCAD (free at openscad.org).

To export the top shell:
1. Comment out `translate([0, -(D*0.42 + 14), 0]) battery_lid();` at the bottom
2. Press F6 to render
3. File > Export > Export as STL → save as `controller_top_shell.stl`

To export the battery lid:
1. Comment out `top_shell();` at the bottom
2. Remove the `translate(...)` wrapper around `battery_lid();`
3. Press F6 to render
4. File > Export > Export as STL → save as `controller_battery_lid.stl`

## Print Settings

| Setting | Value |
|---|---|
| Material | PETG |
| Infill | 40% |
| Layer height | 0.2mm |
| Perimeters | 3 |
| Supports | Not needed for top shell or lid |
