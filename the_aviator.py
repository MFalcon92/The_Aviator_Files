"""
 _____ _             _           _      _
|_   _| |__   ___   / \__   ___ (_) __ _| |_ ___  _ __
  | | | '_ \ / _ \ / _ \ \ / / | |/ _` | __/ _ \| '__|
  | | | | | |  __// ___ \ V /  | | (_| | || (_) | |
  |_| |_| |_|\___/_/   \_\_/   |_|\__,_|\__\___/|_|

Autonomous Laser-Targeted Claw Drone — Forward Camera / Downward Claw
=======================================================================
Camera orientation : FORWARD-FACING (tracks laser dot horizontally)
Claw orientation   : DOWNWARD-FACING (descends onto target from above)
Sonar orientation  : DOWNWARD-FACING (detects object below + grab distance)

Sequence:
  1. Camera aligns drone left/right with laser dot
  2. Drone climbs until dot is vertically centred (drone at object height)
     Then climbs exactly 5 inches above that
  3. Drone flies straight forward at fixed altitude
     Sonar watches downward — stops the moment it reads ≤ 6.5 inches below
  4. Drone descends — sonar watches distance to object top
  5. Claw closes when sonar reads ≤ SONAR_GRAB_DISTANCE_M, ascends, returns home

Hardware (DRONE):
  - Raspberry Pi 4  +  Pixhawk (ArduCopter GUIDED mode)
  - Pi Camera v2 mounted FORWARD on front arm — laser dot detection
  - Acxiico N20 gear motor via L298N mini H-bridge — claw open/close
  - HC-SR04 ultrasonic sensor facing DOWNWARD — overhead detection + grab distance
  - nRF24L01 radio module — receives commands from handheld controller
  - Electronic power switch (XT60) on main LiPo line
  - Soft shutdown button on Pi power line (GPIO 25)

Hardware (CONTROLLER — Arduino Nano based, see controller/controller.ino):
  - GRAB button, RELEASE button, ARM/LAND toggle, LASER button, POWER OFF button
  - nRF24L01 radio module — transmits to drone
  - 9V battery + 3.3V regulator for nRF24L01

GPIO pin assignments (DRONE Pi):
  GPIO 5  (Pin 29) — HC-SR04 TRIGGER (output)
  GPIO 6  (Pin 31) — HC-SR04 ECHO    (input, via voltage divider)
  GPIO 8  (Pin 24) — nRF24L01 CSN    (SPI CE0)
  GPIO 9  (Pin 21) — nRF24L01 MISO   (SPI0)
  GPIO 10 (Pin 19) — nRF24L01 MOSI   (SPI0)
  GPIO 11 (Pin 23) — nRF24L01 SCLK   (SPI0)
  GPIO 14 (Pin 8)  — UART TX → Pixhawk TELEM2 RX
  GPIO 15 (Pin 10) — UART RX → Pixhawk TELEM2 TX
  GPIO 22 (Pin 15) — L298N IN2 → N20 reverse (claw opens)
  GPIO 25 (Pin 22) — Soft shutdown button (active-LOW)
  GPIO 27 (Pin 13) — L298N IN1 → N20 forward (claw closes)

Requirements:
  pip install dronekit pymavlink opencv-python numpy RPi.GPIO pyrf24
  (pyrf24 is the Python library for nRF24L01)

Run modes:
  python the_aviator.py           # camera test, no drone
  python the_aviator.py --drone   # full autonomous mode
"""

import cv2
import numpy as np
import time
import threading

USE_GPIO = False
if USE_GPIO:
    import RPi.GPIO as GPIO
    import spidev
    from pyrf24 import RF24, RF24_PA_LOW, RF24_250KBPS
    import subprocess

from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil


# ═══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_NAME = "THE AVIATOR"

# ── Camera ─────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0
FRAME_W      = 640
FRAME_H      = 480

# ── Laser detection ────────────────────────────────────────────────────────
USE_IR_LASER            = False
LASER_HSV_LOWER         = np.array([40, 100, 200])   # visible green laser
LASER_HSV_UPPER         = np.array([80, 255, 255])
IR_BRIGHTNESS_THRESHOLD = 240
MIN_BLOB_AREA           = 3
MAX_BLOB_AREA           = 500

# ── Frame alignment tolerance ──────────────────────────────────────────────
# How many pixels from centre counts as "aligned"
# Lateral (left/right in frame)  — tighter because claw has no lateral margin
# Vertical (up/down in frame)    — looser, corrected by altitude hold
ALIGN_TOLERANCE_X = 30   # pixels left/right
ALIGN_TOLERANCE_Y = 40   # pixels up/down

# ── PID — used for lateral/longitudinal alignment ─────────────────────────
PID_KP       = 0.002
PID_KI       = 0.0001
PID_KD       = 0.001
MAX_VELOCITY = 0.8    # m/s cap during alignment

# ── Ultrasonic — DOWNWARD facing ──────────────────────────────────────────
#
# Simple fixed-height strategy:
#
#   1. Camera aligns drone left/right with laser dot.
#   2. Drone climbs to FLY_HEIGHT_ABOVE_OBJECT above the laser dot level.
#      (default 5 inches = 0.127m)
#   3. Drone flies straight forward at that fixed altitude.
#   4. Sonar watches downward. When it reads SONAR_DETECT_DISTANCE or less,
#      the object is directly below — drone stops immediately.
#   5. Drone descends. Sonar watches distance to object top.
#   6. Claw closes when sonar hits SONAR_GRAB_DISTANCE_M.
#
# FLY_HEIGHT_ABOVE_OBJECT: fixed altitude above the object during approach.
#   5 inches (0.127m) keeps the drone low and gives the sonar a short,
#   accurate read distance to work with.
#
# SONAR_DETECT_DISTANCE: the sonar reading that means "object is below me".
#   6.5 inches = 0.165m. The drone is flying 5in above the object, so when
#   the sonar sees ~6.5in (a little more than 5in to account for sensor noise
#   and the object's shape), it stops.
#   Must be larger than FLY_HEIGHT_ABOVE_OBJECT so it actually triggers.
#
# SONAR_GRAB_DISTANCE_M: how close the claw needs to get during descent.
#   0.02m (2cm) — the claw is basically touching the object at this point.
#
FLY_HEIGHT_ABOVE_OBJECT  = 0.127   # 5 inches in metres — approach altitude above object
SONAR_DETECT_DISTANCE    = 0.165   # 6.5 inches in metres — stops approach when sonar reads this
SONAR_GRAB_DISTANCE_M    = 0.02    # metres to object top — claw closes at this distance
SONAR_TIMEOUT_S          = 0.04    # max wait for echo pulse
SONAR_APPROACH_SPEED     = 0.3     # m/s forward during approach



# ── nRF24L01 wireless receiver ─────────────────────────────────────────────
#
# The nRF24L01 receives a 7-byte packet from the Arduino controller
# every ~20ms containing the state of all inputs:
#
#   Byte 2 — buttons bitmask:
#               bit 0 = GRAB
#               bit 1 = RELEASE
#               bit 2 = ARM/LAND toggle
#               bit 3 = LASER (reserved — laser is self-contained on controller)
#               bit 4 = POWER OFF
#   Byte 3–6 — reserved / future use
#
# However pyrf24 manages its own SPI so the two don't conflict.
#
NRF_CE_PIN     = 7    # GPIO 7 — nRF24L01 CE pin
NRF_CHANNEL    = 76   # 2.476 GHz — away from WiFi congestion
NRF_ADDRESS    = b'AVTR1'   # 5-byte pipe address — must match controller

# ── Soft shutdown ──────────────────────────────────────────────────────────
# GPIO 25 is pulled up. Shorting to GND (or controller sending POWER OFF)
# triggers a clean Pi shutdown. Never cut power without this or you risk
# corrupting the SD card.
SHUTDOWN_PIN   = 25   # GPIO 25 (Pin 22) — active-LOW soft shutdown input

# ── ARM/LAND config ────────────────────────────────────────────────────────
TAKEOFF_ALT    = HOME_ALTITUDE   # metres — altitude for auto-takeoff to idle
LAND_DESCENT_SPEED = 0.2         # m/s downward during controlled landing

# ── Flight parameters ──────────────────────────────────────────────────────
HOME_ALTITUDE        = 1.5     # metres — indoor safe default
GRAB_ALTITUDE_OFFSET = 0.127   # 5 inches — ascend this much after grab
DESCENT_SPEED        = 0.15    # m/s downward during grab descent
ASCENT_SPEED         = 0.30    # m/s upward after grab
DESCENT_MIN_ALT      = 0.15    # hard floor metres (lower than outdoor since indoor)
POSITION_TOLERANCE_M = 0.25
ALTITUDE_TOLERANCE_M = 0.08

# ── GPIO pins (BCM) ────────────────────────────────────────────────────────
MOTOR_PIN_FWD    = 27    # L298N IN1 — N20 forward  (closes claw)
MOTOR_PIN_REV    = 22    # L298N IN2 — N20 reverse  (opens  claw)
SONAR_TRIG_PIN   = 5     # HC-SR04 trigger           (output)
SONAR_ECHO_PIN   = 6     # HC-SR04 echo              (input, voltage divider)

# ── N20 claw timing ────────────────────────────────────────────────────────
CLAW_CLOSE_SECONDS = 3.0
CLAW_OPEN_SECONDS  = 3.0

# ── MAVLink ────────────────────────────────────────────────────────────────
MAVLINK_CONNECTION = '/dev/ttyAMA0'
MAVLINK_BAUD       = 57600

# ── Camera geometry ────────────────────────────────────────────────────────
# Forward-facing camera: pixel offset from centre maps to:
#   X (horizontal) → drone lateral movement (left/right)
#   Y (vertical)   → drone altitude adjustment (up/down)
# We do NOT use camera Y for forward/back — that's handled by sonar.
#
# Pixels → metres lateral at typical operating distance (~2–5m range).
# Calibrate by measuring how many pixels a known lateral offset produces.
PX_TO_METRES_LATERAL = 0.004   # at ~3m distance, 1px ≈ 4mm lateral


# ═══════════════════════════════════════════════════════════════════════════
#  CLAW STATE  (simple flag — no longer needed to gate a sensor)
# ═══════════════════════════════════════════════════════════════════════════

_claw_closed = False   # True when claw is holding something


def is_claw_closed():
    return _claw_closed


# ═══════════════════════════════════════════════════════════════════════════
#  DRONE FLIGHT STATE
# ═══════════════════════════════════════════════════════════════════════════

# Tracks whether the drone is armed and airborne.
# DISARMED  — on the ground, motors off, safe to handle
# IDLE      — armed, hovering at HOME_ALTITUDE, ready for commands
# MISSION   — autonomous grab sequence running
FLIGHT_STATE_DISARMED = "DISARMED"
FLIGHT_STATE_IDLE     = "IDLE"
FLIGHT_STATE_MISSION  = "MISSION"
_flight_state      = FLIGHT_STATE_DISARMED
_flight_state_lock = threading.Lock()

def get_flight_state():
    with _flight_state_lock:
        return _flight_state

def set_flight_state(state):
    global _flight_state
    with _flight_state_lock:
        _flight_state = state
    print(f"[STATE] → {state}")


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════

_radio = None   # nRF24L01 radio — initialised in gpio_setup()


# ═══════════════════════════════════════════════════════════════════════════
#  GPIO SETUP / CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def gpio_setup():
    if not USE_GPIO:
        print("[GPIO] Stub mode.")
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(MOTOR_PIN_FWD,  GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(MOTOR_PIN_REV,  GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SONAR_TRIG_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(SONAR_ECHO_PIN, GPIO.IN)
    GPIO.setup(SHUTDOWN_PIN,   GPIO.IN,  pull_up_down=GPIO.PUD_UP)
    print("[GPIO] Pins configured.")
    # nRF24L01 initialisation
    global _radio
    _radio = RF24(NRF_CE_PIN, 0)   # CE pin, SPI bus 0
    _radio.begin()
    _radio.set_pa_level(RF24_PA_LOW)
    _radio.set_data_rate(RF24_250KBPS)
    _radio.channel = NRF_CHANNEL
    _radio.open_reading_pipe(1, NRF_ADDRESS)
    _radio.start_listening()
    print(f"[GPIO] nRF24L01 listening on channel {NRF_CHANNEL}.")


def gpio_cleanup():
    if not USE_GPIO:
        return
    GPIO.output(MOTOR_PIN_FWD,  GPIO.LOW)
    GPIO.output(MOTOR_PIN_REV,  GPIO.LOW)
    GPIO.output(SONAR_TRIG_PIN, GPIO.LOW)
    GPIO.output(MOTOR_PIN_FWD,  GPIO.LOW)
    GPIO.output(MOTOR_PIN_REV,  GPIO.LOW)
    if _radio:
        _radio.stop_listening()
    GPIO.cleanup()


# ═══════════════════════════════════════════════════════════════════════════
#  nRF24L01 WIRELESS RECEIVER  — reads controller packet each frame
# ═══════════════════════════════════════════════════════════════════════════

# Last received controller state — updated every frame by read_controller()
_ctrl = {
    'grab':       False,
    'release':    False,
    'arm_land':   False,
    'power_off':  False,
    'connected':  False,  # True when a packet arrived recently
}
_ctrl_lock        = threading.Lock()
_last_packet_time = 0.0


def read_controller():
    """
    Non-blocking read of the nRF24L01. Updates _ctrl dict if a packet
    is available. Call once per main loop frame.
    Sets _ctrl['connected'] = False if no packet received in 0.5s
    (controller out of range or off).
    """
    global _last_packet_time
    if not USE_GPIO or _radio is None:
        return

    if _radio.available():
        buf = _radio.read(_radio.payload_size)
        bitmask  = buf[2]
        with _ctrl_lock:
            _ctrl['grab']      = bool(bitmask & 0x01)
            _ctrl['release']   = bool(bitmask & 0x02)
            _ctrl['arm_land']  = bool(bitmask & 0x04)
            _ctrl['power_off'] = bool(bitmask & 0x10)
            _ctrl['connected'] = True
        _last_packet_time = time.time()
    else:
        if time.time() - _last_packet_time > 0.5:
            with _ctrl_lock:
                _ctrl['connected'] = False


def ctrl_get():
    """Thread-safe snapshot of current controller state."""
    with _ctrl_lock:
        return dict(_ctrl)





# ═══════════════════════════════════════════════════════════════════════════
#  BUTTON READING  (from wireless controller packet)
# ═══════════════════════════════════════════════════════════════════════════

def btn_grab_pressed():
    return ctrl_get()['grab']

def btn_release_pressed():
    return ctrl_get()['release']

def btn_arm_land_pressed():
    return ctrl_get()['arm_land']

def btn_power_off_pressed():
    """Check both wireless power-off and local hardware shutdown pin."""
    wireless = ctrl_get()['power_off']
    hardware = (USE_GPIO and GPIO.input(SHUTDOWN_PIN) == GPIO.LOW)
    return wireless or hardware


# ═══════════════════════════════════════════════════════════════════════════
#  HC-SR04 ULTRASONIC SENSOR  (DOWNWARD facing — floor/object distance)
# ═══════════════════════════════════════════════════════════════════════════

def sonar_read_metres():
    """
    Fire HC-SR04 and return distance in metres to whatever is below the drone.
    Returns None on timeout.

    Downward-facing:
      - During approach at HOME_ALTITUDE, reads roughly HOME_ALTITUDE (floor).
      - When drone passes over an object, reading drops sharply.
      - During descent, reads the distance to the top of the object.
    """
    if not USE_GPIO:
        return None
    GPIO.output(SONAR_TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(SONAR_TRIG_PIN, GPIO.LOW)
    pulse_start = time.time()
    while GPIO.input(SONAR_ECHO_PIN) == GPIO.LOW:
        if time.time() - pulse_start > SONAR_TIMEOUT_S:
            return None
    pulse_start = time.time()
    while GPIO.input(SONAR_ECHO_PIN) == GPIO.HIGH:
        if time.time() - pulse_start > SONAR_TIMEOUT_S:
            return None
    pulse_end = time.time()
    return (pulse_end - pulse_start) * 343.0 / 2.0


def sonar_object_below():
    """
    Returns True when the sonar reads SONAR_DETECT_DISTANCE or less —
    meaning something is directly below the drone at the expected distance.
    The drone is flying at FLY_HEIGHT_ABOVE_OBJECT (5in) above the object,
    so SONAR_DETECT_DISTANCE (6.5in) is just enough margin for sensor noise
    and object shape variation.
    """
    dist = sonar_read_metres()
    if dist is None:
        return False
    return dist <= SONAR_DETECT_DISTANCE


def sonar_at_grab_distance():
    """
    Returns True when the drone has descended close enough to grab —
    sonar reads SONAR_GRAB_DISTANCE_M or less to the object top.
    """
    dist = sonar_read_metres()
    if dist is None:
        return False
    return dist <= SONAR_GRAB_DISTANCE_M


# ═══════════════════════════════════════════════════════════════════════════
#  N20 CLAW MOTOR  (via L298N H-bridge)
# ═══════════════════════════════════════════════════════════════════════════

def _motor_stop():
    if not USE_GPIO:
        return
    GPIO.output(MOTOR_PIN_FWD, GPIO.LOW)
    GPIO.output(MOTOR_PIN_REV, GPIO.LOW)


def close_claw():
    """Drive N20 forward — closes claw. Blocking."""
    global _claw_closed
    print("[CLAW] Closing (N20 forward)...")
    if USE_GPIO:
        GPIO.output(MOTOR_PIN_REV, GPIO.LOW)
        GPIO.output(MOTOR_PIN_FWD, GPIO.HIGH)
    else:
        print(f"[CLAW] (stub) N20 FWD {CLAW_CLOSE_SECONDS}s")
    time.sleep(CLAW_CLOSE_SECONDS)
    _motor_stop()
    _claw_closed = True
    print("[CLAW] Closed.")


def open_claw():
    """Drive N20 reverse — opens claw. Blocking."""
    global _claw_closed
    print("[CLAW] Opening (N20 reverse)...")
    if USE_GPIO:
        GPIO.output(MOTOR_PIN_FWD, GPIO.LOW)
        GPIO.output(MOTOR_PIN_REV, GPIO.HIGH)
    else:
        print(f"[CLAW] (stub) N20 REV {CLAW_OPEN_SECONDS}s")
    time.sleep(CLAW_OPEN_SECONDS)
    _motor_stop()
    _claw_closed = False
    print("[CLAW] Open.")


def open_claw_async():
    threading.Thread(target=open_claw, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
#  PID CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

class PIDController:
    def __init__(self, kp, ki, kd, max_output=MAX_VELOCITY):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.max_output = max_output
        self.prev_error = 0.0
        self.integral   = 0.0

    def compute(self, error, dt):
        if dt <= 0:
            return 0.0
        self.integral  += error * dt
        self.integral   = float(np.clip(self.integral, -50, 50))
        derivative      = (error - self.prev_error) / dt
        self.prev_error = error
        return float(np.clip(
            self.kp * error + self.ki * self.integral + self.kd * derivative,
            -self.max_output, self.max_output
        ))

    def reset(self):
        self.prev_error = 0.0
        self.integral   = 0.0


# ═══════════════════════════════════════════════════════════════════════════
#  LASER DETECTION  (forward-facing camera)
# ═══════════════════════════════════════════════════════════════════════════

def detect_laser(frame):
    """
    Returns ((cx, cy), mask) or (None, mask).

    Forward camera interpretation:
      cx left of centre  → object is to the LEFT  → drone moves left
      cx right of centre → object is to the RIGHT → drone moves right
      cy above centre    → object is HIGHER        → drone climbs
      cy below centre    → object is LOWER         → drone descends slightly
    """
    if USE_IR_LASER:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, IR_BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY)
    else:
        hsv        = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        color_mask = cv2.inRange(hsv, LASER_HSV_LOWER, LASER_HSV_UPPER)
        _, bright  = cv2.threshold(hsv[:, :, 2], 220, 255, cv2.THRESH_BINARY)
        mask       = cv2.bitwise_and(color_mask, bright)

    k    = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.dilate(mask, k, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, best_area = None, 0
    for c in contours:
        area = cv2.contourArea(c)
        if MIN_BLOB_AREA <= area <= MAX_BLOB_AREA and area > best_area:
            best_area, best = area, c

    if best is not None:
        M = cv2.moments(best)
        if M["m00"] > 0:
            return (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])), mask

    return None, mask


# ═══════════════════════════════════════════════════════════════════════════
#  DRONE CONTROL
# ═══════════════════════════════════════════════════════════════════════════

def connect_drone():
    print("[DRONE] Connecting to Pixhawk...")
    v = connect(MAVLINK_CONNECTION, baud=MAVLINK_BAUD, wait_ready=True)
    print(f"[DRONE] Connected. Mode={v.mode.name}  Armed={v.armed}")
    return v


def send_velocity(vehicle, vx, vy, vz=0.0):
    """
    Body-frame NED velocity.
      vx positive = forward
      vy positive = right
      vz positive = DOWN
    """
    if vehicle is None:
        return
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0,
        mavutil.mavlink.MAV_FRAME_BODY_NED,
        0b0000111111000111,
        0, 0, 0,
        vx, vy, vz,
        0, 0, 0, 0, 0
    )
    vehicle.send_mavlink(msg)


def hover(vehicle):
    send_velocity(vehicle, 0, 0, 0)


def get_altitude(vehicle):
    if vehicle is None:
        return HOME_ALTITUDE
    return vehicle.location.global_relative_frame.alt or 0.0


def arm_and_takeoff(vehicle, target_alt):
    """Arm motors and climb to target_alt. Blocking."""
    if vehicle is None:
        print(f"[TAKEOFF] (stub) Arming and climbing to {target_alt}m")
        time.sleep(2)
        set_flight_state(FLIGHT_STATE_IDLE)
        return
    print("[TAKEOFF] Arming...")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(0.5)
    print(f"[TAKEOFF] Armed. Taking off to {target_alt}m...")
    vehicle.simple_takeoff(target_alt)
    while True:
        alt = get_altitude(vehicle)
        if alt >= target_alt * 0.95:
            break
        time.sleep(0.2)
    hover(vehicle)
    set_flight_state(FLIGHT_STATE_IDLE)
    print("[TAKEOFF] Reached hover altitude — IDLE.")


def land_and_disarm(vehicle):
    """Descend slowly, disarm on touchdown. Blocking."""
    if vehicle is None:
        print("[LAND] (stub) Landing and disarming.")
        time.sleep(2)
        set_flight_state(FLIGHT_STATE_DISARMED)
        return
    print("[LAND] Landing...")
    vehicle.mode = VehicleMode("LAND")
    while get_altitude(vehicle) > 0.1:
        time.sleep(0.3)
    time.sleep(1.5)   # settle on ground
    vehicle.armed = False
    set_flight_state(FLIGHT_STATE_DISARMED)
    print("[LAND] Landed and disarmed.")


def safe_shutdown():
    """Cleanly shut down the Pi after disarming."""
    print("[SHUTDOWN] Safe shutdown initiated...")
    time.sleep(0.5)
    if USE_GPIO:
        import subprocess
        subprocess.call(['sudo', 'shutdown', '-h', 'now'])


def fly_to_position(vehicle, lat, lon, alt, tol=POSITION_TOLERANCE_M):
    if vehicle is None:
        print(f"[NAV] (stub) Flying to ({lat:.6f}, {lon:.6f}) alt={alt:.1f}m")
        time.sleep(2)
        return
    vehicle.simple_goto(LocationGlobalRelative(lat, lon, alt))
    while True:
        loc  = vehicle.location.global_relative_frame
        dlat = abs(loc.lat - lat) * 111320
        dlon = abs(loc.lon - lon) * 111320 * np.cos(np.radians(loc.lat))
        if np.sqrt(dlat**2 + dlon**2) < tol:
            break
        time.sleep(0.2)


def adjust_altitude(vehicle, target_alt, speed=ASCENT_SPEED,
                    tol=ALTITUDE_TOLERANCE_M):
    if vehicle is None:
        print(f"[ALT] (stub) Adjusting to {target_alt:.2f}m")
        time.sleep(2)
        return
    going_down = target_alt < get_altitude(vehicle)
    vz = DESCENT_SPEED if going_down else -ASCENT_SPEED
    while True:
        cur = get_altitude(vehicle)
        if abs(cur - target_alt) < tol:
            break
        if going_down and cur <= DESCENT_MIN_ALT:
            print("[ALT] Safety floor reached.")
            break
        send_velocity(vehicle, 0, 0, vz)
        time.sleep(0.1)
    hover(vehicle)


# ═══════════════════════════════════════════════════════════════════════════
#  COORDINATE HELPERS  (indoor / GPS-denied fallback)
# ═══════════════════════════════════════════════════════════════════════════

def offset_location(lat, lon, d_north, d_east):
    return (
        lat + d_north / 111320.0,
        lon + d_east  / (111320.0 * np.cos(np.radians(lat)))
    )


# ═══════════════════════════════════════════════════════════════════════════
#  MISSION SEQUENCE  (runs in background thread)
# ═══════════════════════════════════════════════════════════════════════════

def run_mission(vehicle, home_lat, home_lon, status, dot_tracker):
    """
    Full grab sequence for forward-camera / downward-claw configuration.

    dot_tracker is a shared dict updated by the main camera loop:
      dot_tracker['error_x']  — pixel offset from centre (+ = dot is right)
      dot_tracker['error_y']  — pixel offset from centre (+ = dot is below)
      dot_tracker['visible']  — True if dot is currently in frame

    Phases:
      1. Align left/right with laser dot (camera X error + PID)
      2. Climb until dot is vertically centred (drone at object height)
         Then climb exactly 5 inches (FLY_HEIGHT_ABOVE_OBJECT) more
      3. Fly straight forward at that fixed altitude
         Sonar watches downward — stops when reading ≤ 6.5in (SONAR_DETECT_DISTANCE)
      4. Open claw
      5. Descend — sonar watches distance to object top
      6. Claw closes when sonar hits SONAR_GRAB_DISTANCE_M
      7. Ascend 5 inches, return home
    """
    pid_lateral  = PIDController(PID_KP, PID_KI, PID_KD)
    pid_vertical = PIDController(PID_KP, PID_KI, PID_KD)

    try:
        # ── 1. Align left/right with laser dot ──────────────────────────
        status['phase'] = "ALIGNING LEFT/RIGHT"
        print("[MISSION] Aligning laterally with laser dot...")

        ALIGN_TIMEOUT = 15.0
        align_start   = time.time()
        prev_time     = time.time()

        while True:
            if time.time() - align_start > ALIGN_TIMEOUT:
                print("[MISSION] Lateral align timeout — aborting.")
                status['phase'] = "ALIGN FAILED — HOVERING"
                hover(vehicle)
                status['done'] = True
                return

            if not dot_tracker['visible']:
                hover(vehicle)
                time.sleep(0.05)
                continue

            ex  = dot_tracker['error_x']
            now = time.time()
            dt  = now - prev_time
            prev_time = now

            vy = pid_lateral.compute(ex, dt)

            if abs(ex) < ALIGN_TOLERANCE_X:
                print("[MISSION] Laterally aligned.")
                hover(vehicle)
                break

            send_velocity(vehicle, 0, vy, 0)
            time.sleep(0.033)

        # ── 2. Climb to 5 inches above the object ────────────────────────
        #
        # The laser dot is on the object. The camera sees the dot in the
        # frame — when the dot is centred vertically, the drone is at the
        # same height as the object. We then climb FLY_HEIGHT_ABOVE_OBJECT
        # (5 inches) further so the claw clears the object during approach.
        #
        # First: climb until dot is vertically centred (drone at object height).
        # Then:  climb exactly FLY_HEIGHT_ABOVE_OBJECT more.
        #
        status['phase'] = "CLIMBING TO OBJECT HEIGHT"
        print("[MISSION] Climbing until dot is vertically centred...")

        CLIMB_TIMEOUT = 20.0
        climb_start   = time.time()
        prev_time     = time.time()

        while True:
            if time.time() - climb_start > CLIMB_TIMEOUT:
                print("[MISSION] Climb timeout — aborting.")
                status['phase'] = "CLIMB FAILED — HOVERING"
                hover(vehicle)
                status['done'] = True
                return

            if not dot_tracker['visible']:
                hover(vehicle)
                time.sleep(0.05)
                continue

            ey  = dot_tracker['error_y']   # + = dot below centre
            ex  = dot_tracker['error_x']
            now = time.time()
            dt  = now - prev_time
            prev_time = now

            vy = pid_lateral.compute(ex, dt) * 0.3   # keep lateral trim

            if abs(ey) < ALIGN_TOLERANCE_Y:
                print("[MISSION] Dot centred vertically — at object height.")
                hover(vehicle)
                break

            # dot below centre → climb; dot above → descend
            vz = pid_vertical.compute(ey, dt) * 0.5  # vz positive = down in NED
            send_velocity(vehicle, 0, vy, vz)
            time.sleep(0.033)

        # Now climb the extra 5 inches above the object
        status['phase'] = "CLIMBING 5in ABOVE OBJECT"
        target_alt = get_altitude(vehicle) + FLY_HEIGHT_ABOVE_OBJECT
        print(f"[MISSION] Climbing {FLY_HEIGHT_ABOVE_OBJECT*39.37:.1f}in "
              f"to {target_alt:.2f}m...")
        adjust_altitude(vehicle, target_alt, speed=ASCENT_SPEED)
        print("[MISSION] At approach altitude — 5 inches above object.")

        # ── 3. Fly forward — sonar stops us when object is below ─────────
        #
        # Drone flies straight forward at fixed altitude (5in above object).
        # Sonar watches downward. When it reads 6.5 inches (0.165m) or less,
        # the object is directly below — stop immediately.
        # The extra 1.5 inches of tolerance above the 5in fly height accounts
        # for sensor noise and uneven object surfaces.
        #
        status['phase'] = "APPROACHING TARGET"
        print(f"[MISSION] Flying forward — stopping when sonar reads "
              f"≤ {SONAR_DETECT_DISTANCE*39.37:.1f}in ({SONAR_DETECT_DISTANCE:.3f}m)...")

        APPROACH_TIMEOUT = 25.0
        approach_start   = time.time()

        while True:
            if time.time() - approach_start > APPROACH_TIMEOUT:
                print("[MISSION] Approach timeout — aborting.")
                status['phase'] = "APPROACH FAILED — HOVERING"
                hover(vehicle)
                status['done'] = True
                return

            dist = sonar_read_metres()
            dist_in  = f"{dist*39.37:.1f}in" if dist is not None else "---"
            dist_str = f"{dist:.3f}m"         if dist is not None else "---"

            # Keep lateral alignment during approach
            if dot_tracker['visible']:
                ex = dot_tracker['error_x']
                vy = pid_lateral.compute(ex, 0.033) * 0.4
            else:
                vy = 0.0

            status['phase'] = f"APPROACHING — sonar: {dist_in}"

            if sonar_object_below():
                print(f"[MISSION] Object below! sonar={dist_in} ({dist_str}). Stopping.")
                hover(vehicle)
                break

            send_velocity(vehicle, SONAR_APPROACH_SPEED, vy, 0)
            time.sleep(0.05)

        # ── 4. Open claw before descending ──────────────────────────────
        status['phase'] = "OPENING CLAW"
        print("[MISSION] Opening claw...")
        open_claw()

        # ── 5. Descend — sonar measures distance to object top ───────────
        #
        # Drone descends slowly. The sonar now reads distance to the top
        # of the object (not the floor — the object is in the way).
        # When it hits SONAR_GRAB_DISTANCE_M the claw is close enough to grab.
        #
        status['phase'] = "DESCENDING — SONAR WATCHING"
        print(f"[MISSION] Descending — will grab at {SONAR_GRAB_DISTANCE_M}m...")

        while True:
            cur_alt = get_altitude(vehicle)
            if cur_alt <= DESCENT_MIN_ALT:
                print("[MISSION] Safety floor reached — aborting grab.")
                status['phase'] = "GRAB FAILED — RETURNING"
                break

            dist = sonar_read_metres()
            dist_str = f"{dist:.3f}m" if dist is not None else "---"
            status['phase'] = f"DESCENDING — {dist_str} to object"

            if sonar_at_grab_distance():
                print(f"[MISSION] At grab distance ({dist_str}) — closing claw!")
                hover(vehicle)
                break

            send_velocity(vehicle, 0, 0, DESCENT_SPEED)
            time.sleep(0.05)

        # ── 6. Close claw ─────────────────────────────────────────────────
        status['phase'] = "CLOSING CLAW"
        close_claw()

        # ── 7. Ascend 5 inches ────────────────────────────────────────────
        status['phase'] = "ASCENDING"
        ascend_to = get_altitude(vehicle) + GRAB_ALTITUDE_OFFSET
        adjust_altitude(vehicle, ascend_to, speed=ASCENT_SPEED)

        # ── 8. Return home ────────────────────────────────────────────────
        status['phase'] = "RETURNING HOME"
        adjust_altitude(vehicle, HOME_ALTITUDE, speed=ASCENT_SPEED)
        if vehicle:
            loc = vehicle.location.global_relative_frame
            home_lat = home_lat or loc.lat
            home_lon = home_lon or loc.lon
        fly_to_position(vehicle, home_lat, home_lon, HOME_ALTITUDE)
        hover(vehicle)

        status['phase'] = "HOME — press RELEASE to drop"
        print("[MISSION] Complete. Holding payload. Press RELEASE to open claw.")

    except Exception as e:
        status['phase'] = f"ERROR: {e}"
        print(f"[MISSION ERROR] {e}")
        hover(vehicle)

    status['done'] = True


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

def run_tracker(vehicle=None):
    gpio_setup()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    CENTER_X = FRAME_W // 2
    CENTER_Y = FRAME_H // 2

    home_lat, home_lon = 0.0, 0.0
    if vehicle:
        loc = vehicle.location.global_relative_frame
        home_lat, home_lon = loc.lat, loc.lon

    # Shared dot tracking state — updated by camera loop, read by mission thread
    dot_tracker = {'error_x': 0, 'error_y': 0, 'raw_cy': 240, 'visible': False}

    dot_locked     = False
    mission_active = False
    mission_status = {'phase': 'IDLE', 'done': False}

    prev_grab_btn    = False
    prev_release_btn = False
    prev_arm_btn     = False

    print(f"\n{'═'*54}")
    print(f"  {PROJECT_NAME}  —  Forward Camera / Downward Claw")
    print(f"{'═'*54}")
    print("  ARM/LAND toggle → arm + takeoff to idle / land + disarm")
    print("  GRAB button     → commit to locked laser target")
    print("  RELEASE button  → open claw / drop payload")
    print("  POWER OFF       → safe Pi shutdown (land first!)")
    print(f"{'═'*54}\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera read failed.")
            break

        # Read wireless controller packet first thing each frame
        read_controller()

        target, mask = detect_laser(frame)

        # ── Update dot tracker ─────────────────────────────────────────────
        if target:
            cx, cy = target
            error_x = cx - CENTER_X   # + = dot is right of centre
            error_y = cy - CENTER_Y   # + = dot is below centre

            dot_tracker['error_x'] = error_x
            dot_tracker['error_y'] = error_y
            dot_tracker['raw_cy']  = cy        # absolute Y pixel for altitude calc
            dot_tracker['visible'] = True
            dot_locked = True

            # Draw dot
            cv2.circle(frame, (cx, cy), 12, (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy),  3, (0, 255, 0), -1)
            cv2.line(frame, (CENTER_X, CENTER_Y), (cx, cy), (0, 255, 0), 1)

            # Alignment zone indicator
            aligned = abs(error_x) < ALIGN_TOLERANCE_X and abs(error_y) < ALIGN_TOLERANCE_Y
            zone_color = (0, 255, 100) if aligned else (0, 180, 255)
            cv2.rectangle(frame,
                (CENTER_X - ALIGN_TOLERANCE_X, CENTER_Y - ALIGN_TOLERANCE_Y),
                (CENTER_X + ALIGN_TOLERANCE_X, CENTER_Y + ALIGN_TOLERANCE_Y),
                zone_color, 1)

            cv2.putText(frame, f"err X:{error_x:+d}  Y:{error_y:+d}px",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
            if aligned:
                cv2.putText(frame, "ALIGNED",
                            (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 100), 2)
        else:
            dot_tracker['visible'] = False
            if not mission_active:
                dot_locked = False
            cv2.putText(frame, "NO LASER DETECTED",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)

        # ── Sonar reading on HUD ───────────────────────────────────────────
        dist = sonar_read_metres()
        dist_str = f"{dist:.2f}m" if dist is not None else "---"
        obj_below  = sonar_object_below()
        sonar_color = (0, 255, 100) if obj_below else (200, 200, 100)
        dist_in_str = f"{dist*39.37:.1f}in" if dist is not None else "---"
        sonar_label = f"SONAR: {dist_in_str} ({dist_str})  stop≤{SONAR_DETECT_DISTANCE*39.37:.1f}in"
        if obj_below:
            sonar_label = f"SONAR: {dist_in_str} — OBJECT BELOW"
        cv2.putText(frame, sonar_label,
                    (10, FRAME_H - 65), cv2.FONT_HERSHEY_SIMPLEX, 0.44, sonar_color, 1)

        # ── Button reading ─────────────────────────────────────────────────
        grab_now    = btn_grab_pressed()
        release_now = btn_release_pressed()
        arm_now     = btn_arm_land_pressed()
        grab_edge    = grab_now and not prev_grab_btn
        release_edge = release_now and not prev_release_btn
        arm_edge     = arm_now  and not prev_arm_btn
        prev_grab_btn    = grab_now
        prev_release_btn = release_now
        prev_arm_btn     = arm_now

        # ── POWER OFF ─────────────────────────────────────────────────────
        if btn_power_off_pressed():
            state = get_flight_state()
            if state != FLIGHT_STATE_DISARMED:
                print("[CTRL] Power off requested but drone is not disarmed — ignoring.")
            else:
                print("[CTRL] Power off — shutting down Pi.")
                cv2.destroyAllWindows()
                cap.release()
                gpio_cleanup()
                if vehicle:
                    vehicle.close()
                safe_shutdown()
                break

        # ── ARM / LAND toggle ─────────────────────────────────────────────
        if arm_edge and not mission_active:
            state = get_flight_state()
            if state == FLIGHT_STATE_DISARMED:
                print("[CTRL] ARM/LAND — arming and taking off.")
                threading.Thread(
                    target=arm_and_takeoff,
                    args=(vehicle, TAKEOFF_ALT),
                    daemon=True
                ).start()
            elif state == FLIGHT_STATE_IDLE:
                print("[CTRL] ARM/LAND — landing and disarming.")
                threading.Thread(
                    target=land_and_disarm,
                    args=(vehicle,),
                    daemon=True
                ).start()

        if grab_edge and not mission_active:
            if get_flight_state() != FLIGHT_STATE_IDLE:
                print("[BTN] GRAB — drone not in IDLE, ignoring.")
            elif dot_locked:
                print("[BTN] GRAB — committing to target.")
                set_flight_state(FLIGHT_STATE_MISSION)
                mission_active = True
                mission_status = {'phase': 'STARTING', 'done': False}
                threading.Thread(
                    target=run_mission,
                    args=(vehicle, home_lat, home_lon, mission_status, dot_tracker),
                    daemon=True
                ).start()
            else:
                print("[BTN] GRAB — no target locked.")

        if release_edge:
            if not is_claw_closed():
                print("[BTN] RELEASE — claw already open.")
            else:
                print("[BTN] RELEASE — opening claw.")
                open_claw_async()

        # Keyboard Q to quit during testing
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if mission_active and mission_status['done']:
            mission_active = False
            dot_locked     = False

        # ── HUD ────────────────────────────────────────────────────────────
        phase       = mission_status['phase']
        closed      = is_claw_closed()
        claw_label  = "CLOSED" if closed else "OPEN"
        claw_color  = (0, 100, 255) if closed else (0, 255, 100)
        p_color     = (0, 255, 255) if mission_active else (180, 180, 180)
        fstate      = get_flight_state()
        fstate_col  = {
            FLIGHT_STATE_DISARMED: (80,  80,  80),
            FLIGHT_STATE_IDLE:     (0,   255, 100),
            FLIGHT_STATE_MISSION:  (0,   200, 255),
        }.get(fstate, (180, 180, 180))
        ctrl        = ctrl_get()
        ctrl_col    = (0, 255, 100) if ctrl['connected'] else (0, 60, 255)
        ctrl_label  = "CTRL: CONNECTED" if ctrl['connected'] else "CTRL: NO SIGNAL"

        cv2.putText(frame, PROJECT_NAME,
                    (CENTER_X - 90, FRAME_H - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1)
        cv2.drawMarker(frame, (CENTER_X, CENTER_Y),
                       (255, 255, 255), cv2.MARKER_CROSS, 20, 1)

        # Camera orientation label
        cv2.putText(frame, "CAM: FORWARD  |  CLAW: DOWN  |  SONAR: DOWN",
                    (CENTER_X - 170, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 200), 1)

        # Top-right status
        cv2.putText(frame, fstate,
                    (FRAME_W - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, fstate_col, 2)
        cv2.putText(frame, f"CLAW: {claw_label}",
                    (FRAME_W - 200, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, claw_color, 2)
        cv2.putText(frame, ctrl_label,
                    (FRAME_W - 200, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.45, ctrl_col, 1)
        if dot_locked and not mission_active:
            cv2.putText(frame, "TARGET LOCKED",
                        (FRAME_W - 200, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 100), 2)

        # Bottom status
        cv2.putText(frame, f"PHASE: {phase}",
                    (10, FRAME_H - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, p_color, 2)
        if mission_active:
            hint = "MISSION IN PROGRESS"
        elif fstate == FLIGHT_STATE_DISARMED:
            hint = "DISARMED — toggle ARM/LAND to take off"
        else:
            hint = "IDLE — GRAB=commit  RELEASE=drop"
        cv2.putText(frame, hint,
                    (10, FRAME_H - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 150, 150), 1)

        cv2.imshow(PROJECT_NAME, frame)
        cv2.imshow("Detection Mask", mask)

    cap.release()
    cv2.destroyAllWindows()
    gpio_cleanup()
    if vehicle:
        hover(vehicle)
        vehicle.close()
    print(f"\n[{PROJECT_NAME}] Shutdown complete.")


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    use_drone = "--drone" in sys.argv
    vehicle   = None

    if use_drone:
        vehicle = connect_drone()
        vehicle.mode = VehicleMode("GUIDED")
        time.sleep(1)

    try:
        run_tracker(vehicle)
    except KeyboardInterrupt:
        print(f"\n[{PROJECT_NAME}] Interrupted.")
        if vehicle:
            hover(vehicle)
            vehicle.close()
        gpio_cleanup()