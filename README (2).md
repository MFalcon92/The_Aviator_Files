# cad/claw_mechanism

3-finger downward-facing claw driven by the Acxiico N20 gear motor.

## Design Requirements

- 3-finger symmetric grip (prevents tipping under uneven loads)
- Centre-mounted under drone — off-centre by even 1-2cm causes tilt under load
- Sonar clearance — HC-SR04 mounts at centre pointing down; claw arms must never enter the sonar beam
- N20 motor mount — 3mm D-shaft, motor sits inside or beside claw body
- Rubber or silicone grip pads on finger tips for smooth objects (glass, apple)
- Rated for 500g minimum payload

## Files to Add

| Filename | Format | Description |
|---|---|---|
| `claw_body.stl` | STL | Main claw body |
| `claw_finger.stl` | STL | Single finger — print x3 |
| `claw_motor_mount.stl` | STL | N20 motor holder |
| `claw_assembly.step` | STEP | Full parametric assembly |
| `claw_assembly.f3d` | Fusion 360 | Editable source |

## Print Settings

| Setting | Value |
|---|---|
| Material | PETG |
| Infill | 50% |
| Layer height | 0.15mm |
| Supports | Yes — finger joint overhangs |

## Motor Specs (Acxiico N20)

| Spec | Value |
|---|---|
| Voltage | 3–6V (run at 5V) |
| Shaft | 3mm D-type |
| Recommended gearing | 50–100 RPM for fragile payloads |
| Current (stall) | ~250mA |
