# pcb/drone_sensor_board

Sensor interface board for the Raspberry Pi — eliminates loose Dupont wires that vibrate loose in flight.

## Integrates

- Pi 40-pin GPIO header (stacks on Pi or connects via short ribbon)
- nRF24L01 module socket (2×4 pin, 3.3V)
- HC-SR04 sonar connector with built-in 1kΩ/2kΩ ECHO voltage divider
- L298N module connector (6-pin JST)
- Shutdown button connector (2-pin JST)
- Pixhawk TELEM2 header (3-pin: TX, RX, GND)
- 100µF cap across nRF VCC/GND

## Built-In Voltage Divider

The ECHO voltage divider is on-board — no external resistors needed:

```
HC-SR04 ECHO (5V) → [1kΩ trace] → GPIO6
                                       |
                                    [2kΩ trace]
                                       |
                                      GND
```

## Files to Add

| Filename | Format | Description |
|---|---|---|
| `drone_sensor_board.kicad_sch` | KiCad | Schematic |
| `drone_sensor_board.kicad_pcb` | KiCad | PCB layout |
| `drone_sensor_board_gerbers.zip` | Gerber | Send to fab |

## PCB Specs

| Spec | Value |
|---|---|
| Board size | ~65 × 56mm (Pi footprint) |
| Layers | 2 |
| Mounting | Stacks on Pi GPIO header |
| Thickness | 1.6mm |

## GPIO Routing

| Pi GPIO | Pin | Dir | Connects To |
|---|---|---|---|
| GPIO5  | 29 | OUT | HC-SR04 TRIG |
| GPIO6  | 31 | IN  | HC-SR04 ECHO (via divider) |
| GPIO7  | 26 | OUT | nRF24L01 CE |
| GPIO8  | 24 | SPI | nRF24L01 CSN |
| GPIO9  | 21 | SPI | nRF24L01 MISO |
| GPIO10 | 19 | SPI | nRF24L01 MOSI |
| GPIO11 | 23 | SPI | nRF24L01 SCK |
| GPIO14 | 8  | TX  | Pixhawk TELEM2 RX |
| GPIO15 | 10 | RX  | Pixhawk TELEM2 TX |
| GPIO22 | 15 | OUT | L298N IN2 (open claw) |
| GPIO25 | 22 | IN  | Shutdown button |
| GPIO27 | 13 | OUT | L298N IN1 (close claw) |
