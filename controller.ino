/*
 _____ _             _           _      _
|_   _| |__   ___   / \__   ___ (_) __ _| |_ ___  _ __
  | | | '_ \ / _ \ / _ \ \ / / | |/ _` | __/ _ \| '__|
  | | | | | |  __// ___ \ V /  | | (_| | || (_) | |
  |_| |_| |_|\___/_/   \_\_/   |_|\__,_|\__\___/|_|

THE AVIATOR — Handheld Controller
===================================
Microcontroller : Arduino Nano
Radio           : nRF24L01 (2.4GHz, 100m+ range)

Buttons (5 total — no joystick):
  D2  — ARM/LAND toggle   (momentary push, active-LOW)
  D3  — GRAB button       (momentary push, active-LOW)
  D4  — RELEASE button    (momentary push, active-LOW)
  D5  — LASER button      (hold to fire laser, active-LOW)
  D6  — POWER OFF button  (momentary push, active-LOW)
  D7  — Laser transistor output (drives 2N2222 base via 1k resistor)

nRF24L01 wiring (SPI):
  nRF VCC  → Arduino 3.3V   (MUST be 3.3V — 5V destroys module)
  nRF GND  → Arduino GND
  nRF CE   → D9
  nRF CSN  → D10
  nRF SCK  → D13
  nRF MOSI → D11
  nRF MISO → D12
  + 100uF cap between nRF VCC and GND (solder directly to module)

Power:
  9V battery → Arduino Vin

Packet format (7 bytes sent every 20ms):
  [0] 0x00 (reserved — joystick removed)
  [1] 0x00 (reserved)
  [2] button bitmask:
        bit 0 = GRAB
        bit 1 = RELEASE
        bit 2 = ARM/LAND
        bit 3 = LASER
        bit 4 = POWER OFF
  [3-6] reserved, 0x00

Libraries required (Arduino Library Manager):
  RF24 by TMRh20
*/

#include <SPI.h>
#include <RF24.h>

// ── Pin assignments ──────────────────────────────────────────
const int PIN_BTN_ARM    = 2;
const int PIN_BTN_GRAB   = 3;
const int PIN_BTN_RELEASE= 4;
const int PIN_BTN_LASER  = 5;
const int PIN_BTN_PWROFF = 6;
const int PIN_LASER_OUT  = 7;
const int PIN_NRF_CE     = 9;
const int PIN_NRF_CSN    = 10;

// ── Radio ────────────────────────────────────────────────────
RF24 radio(PIN_NRF_CE, PIN_NRF_CSN);
const byte ADDRESS[6]    = "AVTR1";  // must match NRF_ADDRESS in the_aviator.py
const int  CHANNEL       = 76;       // must match NRF_CHANNEL in the_aviator.py

uint8_t packet[7];

// ── Button debouncer ─────────────────────────────────────────
struct Button {
    int  pin;
    bool last_state;
    unsigned long last_ms;
    static const int DEBOUNCE_MS = 30;

    void begin(int p) {
        pin        = p;
        last_state = HIGH;
        last_ms    = 0;
        pinMode(pin, INPUT_PULLUP);
    }

    bool pressed() {
        bool reading = digitalRead(pin);
        if (reading != last_state) {
            last_ms    = millis();
            last_state = reading;
        }
        if ((millis() - last_ms) > DEBOUNCE_MS)
            return (last_state == LOW);  // active-LOW: LOW = pressed
        return false;
    }
};

Button btnArm, btnGrab, btnRelease, btnLaser, btnPwrOff;

const unsigned long SEND_INTERVAL_MS = 20;  // 50Hz
unsigned long last_send_ms = 0;


void setup() {
    Serial.begin(115200);

    btnArm.begin(PIN_BTN_ARM);
    btnGrab.begin(PIN_BTN_GRAB);
    btnRelease.begin(PIN_BTN_RELEASE);
    btnLaser.begin(PIN_BTN_LASER);
    btnPwrOff.begin(PIN_BTN_PWROFF);

    pinMode(PIN_LASER_OUT, OUTPUT);
    digitalWrite(PIN_LASER_OUT, LOW);

    if (!radio.begin()) {
        Serial.println("[CTRL] nRF24L01 not found — check wiring!");
        while (1) {}
    }
    radio.setPALevel(RF24_PA_LOW);
    radio.setDataRate(RF24_250KBPS);
    radio.setChannel(CHANNEL);
    radio.openWritingPipe(ADDRESS);
    radio.stopListening();

    Serial.println("[CTRL] THE AVIATOR controller ready.");
    Serial.println("[CTRL] Buttons: ARM/LAND=D2  GRAB=D3  RELEASE=D4  LASER=D5  PWROFF=D6");
}


void loop() {
    unsigned long now = millis();
    if (now - last_send_ms < SEND_INTERVAL_MS) return;
    last_send_ms = now;

    // ── Read buttons ─────────────────────────────────────────
    bool arm     = btnArm.pressed();
    bool grab    = btnGrab.pressed();
    bool release = btnRelease.pressed();
    bool laser   = btnLaser.pressed();
    bool pwroff  = btnPwrOff.pressed();

    // ── Drive laser locally ───────────────────────────────────
    digitalWrite(PIN_LASER_OUT, laser ? HIGH : LOW);

    // ── Build packet ──────────────────────────────────────────
    packet[0] = 0x00;   // reserved (was joystick high byte)
    packet[1] = 0x00;   // reserved (was joystick low byte)
    packet[2] = (grab    ? 0x01 : 0)
              | (release ? 0x02 : 0)
              | (arm     ? 0x04 : 0)
              | (laser   ? 0x08 : 0)
              | (pwroff  ? 0x10 : 0);
    packet[3] = 0;
    packet[4] = 0;
    packet[5] = 0;
    packet[6] = 0;

    // ── Transmit ──────────────────────────────────────────────
    bool ok = radio.write(packet, sizeof(packet));

    // Debug (comment out for production)
    Serial.print("[TX] btn=0b");
    Serial.print(packet[2], BIN);
    Serial.print("  ARM=");    Serial.print(arm);
    Serial.print("  GRAB=");   Serial.print(grab);
    Serial.print("  REL=");    Serial.print(release);
    Serial.print("  LASER=");  Serial.print(laser);
    Serial.print("  PWROFF="); Serial.print(pwroff);
    Serial.println(ok ? "  OK" : "  FAIL");
}
