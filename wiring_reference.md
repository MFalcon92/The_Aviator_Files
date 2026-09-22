# The Aviator — Wiring Reference

Place completed wiring diagram images here (Fritzing exports, draw.io exports, photos).

---

## System Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         DRONE SYSTEM                             │
│                                                                  │
│  [4S LiPo 6000mAh]                                              │
│       │                                                          │
│  [XT60 Power Switch]  ←── flip to power drone on/off            │
│       │                                                          │
│  [PDB Power Distribution Board]                                  │
│   ├── [ESC x6] ──── [SunnySky X2216 Motor x6] ── [Props]        │
│   └── [UBEC 5V] ─── [Raspberry Pi 4]                            │
│                            │                                     │
│            ┌───────────────┼────────────────────┐               │
│            │               │                    │               │
│     [UART TX/RX]    [SPI nRF24L01]        [Pi Camera v2]        │
│            │          Radio RX               FORWARD            │
│     [Pixhawk 2.4.8]                                             │
│      ├── [GPS M8N]                                              │
│      ├── [SiK Telemetry] ─── (to ground station PC)            │
│      ├── [RC Receiver]   ─── (safety pilot override)           │
│      └── [ESC PWM x6]                                          │
│                                                                  │
│            ┌───────────────┬────────────────────┐               │
│            │               │                    │               │
│     [GPIO27/22]      [GPIO5/6]             [GPIO25]             │
│     [L298N H-Bridge]  [HC-SR04 Sonar]    [Shutdown Btn]         │
│     [N20 Claw Motor]   DOWNWARD                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

                   )))  2.4GHz nRF24L01 wireless  (((

┌──────────────────────────────────────────────────────────────────┐
│                      CONTROLLER SYSTEM                           │
│                                                                  │
│  [9V Battery]                                                    │
│       │                                                          │
│  [Arduino Nano]                                                  │
│   ├── D2  ──── [ARM/LAND Button]                                 │
│   ├── D3  ──── [GRAB Button]                                     │
│   ├── D4  ──── [RELEASE Button]                                  │
│   ├── D5  ──── [LASER Button]                                    │
│   ├── D6  ──── [POWER OFF Button]                                │
│   ├── D7  ──[1kΩ]── [2N2222] ── [5mW Laser Module]              │
│   └── SPI ──── [nRF24L01] Radio TX                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Voltage Divider — HC-SR04 ECHO (5V → 3.3V)

```
HC-SR04 ECHO pin (5V output)
          │
        [1kΩ]
          │
          ├──────────────── GPIO6 Pin 31 (reads ~3.3V)
          │
        [2kΩ]
          │
         GND
```

Formula: V_out = 5V × 2000 / (1000 + 2000) = 3.33V

---

## 2N2222 Laser Driver Circuit

```
Arduino D7 ──[1kΩ]──── 2N2222 BASE
                        2N2222 COLLECTOR ──── Laser module (+)
                        2N2222 EMITTER  ──── GND
                        Laser module (-)──── GND
```

D7 HIGH → transistor saturates → laser powers on  
D7 LOW  → transistor cuts off  → laser off

---

## nRF24L01 Power Filter (both drone and controller)

```
nRF24L01 VCC ──┬──────── 3.3V supply
               │
            [100µF]   ← + leg toward VCC
               │
nRF24L01 GND ──┴──────── GND
```

Solder directly to the nRF24L01 module pins before mounting.

---

## Drone GPIO Summary

| GPIO | Pi Pin | Dir | Connected To |
|------|--------|-----|-------------|
| GPIO5  | 29 | OUT | HC-SR04 TRIG |
| GPIO6  | 31 | IN  | HC-SR04 ECHO (via 1k/2k divider) |
| GPIO7  | 26 | OUT | nRF24L01 CE |
| GPIO8  | 24 | SPI | nRF24L01 CSN |
| GPIO9  | 21 | SPI | nRF24L01 MISO |
| GPIO10 | 19 | SPI | nRF24L01 MOSI |
| GPIO11 | 23 | SPI | nRF24L01 SCK |
| GPIO14 | 8  | TX  | Pixhawk TELEM2 RX |
| GPIO15 | 10 | RX  | Pixhawk TELEM2 TX |
| GPIO22 | 15 | OUT | L298N IN2 — claw opens |
| GPIO25 | 22 | IN  | Hardware shutdown button |
| GPIO27 | 13 | OUT | L298N IN1 — claw closes |

---

## Controller Arduino Pin Summary

| Pin | Direction | Connected To |
|-----|-----------|-------------|
| D2  | INPUT     | ARM/LAND button (active-LOW) |
| D3  | INPUT     | GRAB button (active-LOW) |
| D4  | INPUT     | RELEASE button (active-LOW) |
| D5  | INPUT     | LASER button (active-LOW) |
| D6  | INPUT     | POWER OFF button (active-LOW) |
| D7  | OUTPUT    | 2N2222 base via 1kΩ → laser |
| D9  | OUTPUT    | nRF24L01 CE |
| D10 | OUTPUT    | nRF24L01 CSN |
| D11 | SPI MOSI  | nRF24L01 MOSI |
| D12 | SPI MISO  | nRF24L01 MISO |
| D13 | SPI SCLK  | nRF24L01 SCK |

---

## Suggested Diagram Images to Add Here

| Filename | Tool | Description |
|---|---|---|
| `01_power_distribution.png` | Fritzing | LiPo → switch → PDB → UBEC → Pi |
| `02_pixhawk_wiring.png` | Fritzing | Pixhawk TELEM2 → Pi UART, RC, GPS |
| `03_pi_gpio.png` | Fritzing | Pi GPIO → L298N, HC-SR04, nRF24L01 |
| `04_voltage_divider.png` | draw.io | HC-SR04 ECHO 5V → 1k/2k → GPIO6 |
| `06_system_overview.png` | draw.io | Full drone + controller block diagram |