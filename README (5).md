# pcb/controller_pcb

Custom PCB for the handheld controller — replaces loose breadboard wiring inside the enclosure.

## Integrates

- Arduino Nano socket (2×15 pin)
- nRF24L01 module socket (2×4 pin, 3.3V)
- KY-023 joystick connector (4-pin JST)
- 5× push button footprints (through-hole)
- 2N2222 transistor + 1kΩ base resistor footprint
- Laser module connector (2-pin JST)
- 9V battery connector (JST-PH 2-pin)
- 100µF cap across nRF VCC/GND

## Files to Add

| Filename | Format | Description |
|---|---|---|
| `controller_pcb.kicad_sch` | KiCad | Schematic |
| `controller_pcb.kicad_pcb` | KiCad | PCB layout |
| `controller_pcb_gerbers.zip` | Gerber | Send to fab (JLCPCB / PCBWay) |
| `controller_pcb_bom.csv` | CSV | Component placement list |

## PCB Specs

| Spec | Value |
|---|---|
| Board size | ~100 × 70mm |
| Layers | 2 |
| Thickness | 1.6mm |
| Copper weight | 1oz |
| Surface finish | HASL lead-free |

## Net List

| Net | From | To |
|---|---|---|
| VCC_9V | Battery + | Arduino Vin |
| VCC_5V | Arduino 5V | KY-023 VCC |
| VCC_3V3 | Arduino 3V3 | nRF VCC, cap + |
| GND | Battery − | All GND |
| JOY_Y | KY-023 VRy | Arduino A0 |
| NRF_CE | Arduino D9 | nRF CE |
| NRF_CSN | Arduino D10 | nRF CSN |
| NRF_SCK | Arduino D13 | nRF SCK |
| NRF_MOSI | Arduino D11 | nRF MOSI |
| NRF_MISO | Arduino D12 | nRF MISO |
| BTN_ARM | Arduino D2 | Button + GND |
| BTN_GRAB | Arduino D3 | Button + GND |
| BTN_RELEASE | Arduino D4 | Button + GND |
| BTN_LASER | Arduino D5 | Button + GND |
| BTN_PWROFF | Arduino D6 | Button + GND |
| LASER_DRV | Arduino D7 | 1kΩ → 2N2222 base |
