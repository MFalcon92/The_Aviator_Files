# THE AVIATOR
### Autonomous Laser-Targeted Claw Drone

> Point a laser at any object. Press GRAB. The drone finds it, flies to it, picks it up, and brings it back.

---

## What It Does

The Aviator is a fully autonomous hexacopter with a motorised grabbing claw, controlled by a custom handheld wireless controller. It uses a forward-facing camera to lock onto a laser dot and a downward-facing ultrasonic sonar to detect and grab everyday objects; staplers, apples, a glass of water; without any direct piloting.

**The grab sequence:**

1. Point the laser at the target object
2. The drone's camera locks onto the dot; **TARGET LOCKED** shows on the HUD
3. Press **GRAB**
4. Drone aligns left/right with the dot, climbs to 5 inches above object height, and flies forward
5. Sonar detects object below (reads ≤ 6.5in); drone stops directly above
6. Claw opens, drone descends slowly
7. Sonar reads ≤ 2cm to object; claw closes and grabs
8. Drone ascends 5 inches, returns home, hovers
9. Press **RELEASE** to drop

---

## Repository Structure

```
the-aviator/
│
├── README.md                          ← This file
├── LICENSE
├── .gitignore
│
├── assets/
│   ├── BOM.csv                        ← Full bill of materials with costs
│   └── wiring_reference.md            ← ASCII wiring diagrams and GPIO tables
│
├── cad/
│   ├── drone_frame/                   ← Pi and sonar mounting plates
│   ├── claw_mechanism/                ← 3-finger N20-driven claw (STL/STEP/F3D)
│   ├── camera_mount/                  ← Forward-facing Pi Camera bracket
│   └── controller_enclosure/          ← Handheld controller housing
│
├── firmware/
│   ├── drone/
│   │   ├── the_aviator.py             ← Main drone Python firmware (Raspberry Pi 4)
│   │   ├── requirements.txt           ← Python dependencies
│   │   └── README.md
│   ├── controller/
│   │   ├── controller.ino             ← Arduino Nano controller firmware
│   │   └── README.md
│   └── ardupilot_params.param         ← ArduCopter parameter file for Pixhawk
│
└── pcb/
    ├── controller_pcb/                ← Arduino + buttons + radio PCB (KiCad)
    └── drone_sensor_board/            ← Pi sensor breakout with voltage divider (KiCad)
```

---

## System Overview

Two completely independent wireless systems — no physical connection between them.

```
DRONE                                     CONTROLLER
─────                                     ──────────
Raspberry Pi 4                            Arduino Nano
Pi Camera v2 (forward-facing)             Buttons: GRAB, RELEASE,
HC-SR04 sonar (downward-facing)                    ARM/LAND, LASER, POWER OFF
N20 claw + L298N H-bridge                5mW green laser pointer
nRF24L01 receiver          )))   (((     nRF24L01 transmitter
Tarot FY690S 690mm hex frame             9V battery
6× SunnySky X2216 800KV motors
4S 6000mAh LiPo + XT60 power switch
```

**Flight states:**

| State | Description |
|---|---|
| `DISARMED` | On the ground, motors off, Pi running, safe to approach |
| `IDLE` | Armed, hovering at 1.5m. All controller inputs active |
| `MISSION` | Autonomous grab sequence. Manual inputs paused |

---

## Quick Start

### Drone Firmware (Raspberry Pi)

```bash
# Clone the repo onto the Pi
git clone https://github.com/yourusername/the-aviator.git
cd the-aviator/firmware/drone

# Enable SPI and UART
sudo raspi-config
# → Interface Options → SPI → On
# → Interface Options → Serial Port → disable login shell → enable hardware

# Install Python dependencies
pip install -r requirements.txt --break-system-packages

# Test without drone (camera + HUD only)
python the_aviator.py

# Full autonomous mode
python the_aviator.py --drone
```

### Controller Firmware (Arduino Nano)

```
1. Open firmware/controller/controller.ino in Arduino IDE
2. Install RF24 library: Tools → Manage Libraries → search "RF24 by TMRh20"
3. Board: Arduino Nano  |  Processor: ATmega328P
4. Upload
5. Serial Monitor at 115200 baud — confirm [TX] packets every 20ms
```

### Pixhawk (ArduCopter)

```
1. Flash ArduCopter via Mission Planner
2. Load firmware/ardupilot_params.param
3. Run: accelerometer cal, compass cal, radio cal, ESC cal
4. Test hover in STABILIZE before using GUIDED / autonomous mode
```

---

## Key Configuration

All tunable values live at the top of `firmware/drone/the_aviator.py`:

| Variable | Default | Description |
|---|---|---|
| `HOME_ALTITUDE` | `1.5m` | Hover and cruise altitude |
| `FLY_HEIGHT_ABOVE_OBJECT` | `0.127m` (5in) | Approach height above object |
| `SONAR_DETECT_DISTANCE` | `0.165m` (6.5in) | Sonar reading that stops approach |
| `SONAR_GRAB_DISTANCE_M` | `0.02m` | Sonar reading that closes claw |
| `DESCENT_SPEED` | `0.15 m/s` | Descent speed during grab |
| `NRF_CHANNEL` | `76` | Radio channel (must match controller.ino) |
| `NRF_ADDRESS` | `b'AVTR1'` | Radio address (must match controller.ino) |
| `USE_GPIO` | `False` | Set `True` on actual Raspberry Pi hardware |

---

## Bill of Materials

See [`assets/BOM.csv`](assets/BOM.csv) for the full parts list.

| Category | Cost Range |
|---|---|
| Hexacopter flight platform | $293 – $442 |
| Raspberry Pi + camera + radio | $73 – $124 |
| Claw + sonar + sensors | $21 – $40 |
| Handheld controller | $24 – $50 |
| Spares and extras | $20 – $30 |
| **Total** | **$431 – $686** |

---

## Safety

- **Always have a safety pilot** with RC override ready during autonomous flight
- **Altitude fence** set to 3m by default — raise `FENCE_ALT_MAX` for outdoor use
- **Never cut Pi power** without using POWER OFF first — corrupts the SD card
- **Never fly over people** — the claw can drop its payload
- **Check prop direction** before every flight — reversed props will flip the drone instantly
- **Laser** — 5mW is eye-safe at range but never aim at faces or aircraft

---

## Contributing

Pull requests welcome. Open areas:

- CAD files (claw, camera mount, controller enclosure) — STL/STEP/F3D
- KiCad PCB designs for controller board and drone sensor board
- Wiring diagram images (Fritzing preferred)
- Optical flow (PMW3901) integration for reliable indoor position hold

---

## License

MIT — see [LICENSE](LICENSE). Free to build, modify, and share.
