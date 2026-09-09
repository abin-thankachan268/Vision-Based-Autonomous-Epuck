from controller import Robot, Motor, DistanceSensor, Camera, Receiver

# =========================
# ROBOT & DEVICES
# =========================
robot = Robot()
timestep = int(robot.getBasicTimeStep())

# Motors
left_motor = robot.getDevice('left wheel motor')
right_motor = robot.getDevice('right wheel motor')
left_motor.setPosition(float('inf'))
right_motor.setPosition(float('inf'))
left_motor.setVelocity(0.0)
right_motor.setVelocity(0.0)

# Ground sensors (line following)
gs = []
for name in ['gs0', 'gs1', 'gs2']:
    s = robot.getDevice(name)
    s.enable(timestep)
    gs.append(s)

# IR distance sensors (front left & right)
ir0 = robot.getDevice('ir0')
ir1 = robot.getDevice('ir1')
ir0.enable(timestep)
ir1.enable(timestep)

# Camera
camera = robot.getDevice('camera')
camera.enable(timestep)

# Receiver (from supervisor distances). E-puck PROTO exposes a built-in receiver named "receiver".
sup_receiver = robot.getDevice('receiver')
sup_receiver.enable(timestep)

# =========================
# CONSTANTS
# =========================
MAX_SPEED = 6.28
BASE_SPEED = 5.0

LINE_THRESHOLD = 750

# Distance at which to stop for the pedestrian (meters, from supervisor)
PED_STOP_DISTANCE = 0.20

RED_T = 120
BLUE_T = 120
COLOR_DOM = 1.4

# Avoidance durations for each phase (curved, wide path)
PHASE1_DURATION = 80     # slight right arc
PHASE2_DURATION = 160    # long left arc
PHASE3_MAX      = 250    # left arc until line

# Curved arc speeds (both positive -> always moving forward)
ARC_FAST = 5.0           # faster wheel
ARC_SLOW = 3.5           # slower wheel

# IR threshold: how close blue object must be to start avoidance
BLUE_NEAR_IR = 350.0     # tune if needed

# =========================
# STATE VARIABLES
# =========================
blue_avoid_state = None
blue_state_timer = 0
red_detected = False
sup_ped_distance = None
sup_obs_distance = None
sup_time = None
status_line_active = False
last_status_time = -1.0
last_ped_shown = None
last_obs_shown = None
STATUS_MIN_DT = 1.5   # seconds between status prints
STATUS_DELTA = 0.05   # meters change needed to force a print

print("E-PUCK CONTROLLER - LINE FOLLOWING + CURVED BLUE AVOIDANCE")
print("Sequence: RIGHT arc -> LEFT arc -> LEFT arc (find line)")
print()


# =========================
# COLOR DETECTION (ORIGINAL STYLE)
# =========================
def red_in_center(img, w, h):
    """Return True if red object is in central region."""
    red_cnt = 0
    total = 0
    for y in range(h // 3, 2 * h // 3, 2):
        for x in range(w // 3, 2 * w // 3, 2):
            r = camera.imageGetRed(img, w, x, y)
            g = camera.imageGetGreen(img, w, x, y)
            b = camera.imageGetBlue(img, w, x, y)

            if r > RED_T and r > g * COLOR_DOM and r > b * COLOR_DOM:
                red_cnt += 1
            total += 1

    return (red_cnt / total) > 0.10 if total > 0 else False


def blue_in_bottom(img, w, h):
    """Return True if blue object is in bottom region (as in your original)."""
    blue_cnt = 0
    total = 0

    y_start = int(h * 0.65)
    y_end = h - 2

    for y in range(y_start, y_end, 2):
        for x in range(w // 3, 2 * w // 3, 2):
            r = camera.imageGetRed(img, w, x, y)
            g = camera.imageGetGreen(img, w, x, y)
            b = camera.imageGetBlue(img, w, x, y)

            if b > BLUE_T and b > r * COLOR_DOM and b > g * COLOR_DOM:
                blue_cnt += 1
            total += 1

    return (blue_cnt / total) > 0.12 if total > 0 else False


# =========================
# DISTANCE CALCULATION
# =========================
def calculate_distance_from_ir(ir_value):
    """
    Convert IR sensor value to distance in cm.
    IR sensor output is inversely proportional to distance.
    Adjust coefficients based on your sensor calibration.
    """
    if ir_value < 50:
        return float('inf')  # Too far to measure
    # Empirical formula: distance = k / ir_value
    # Adjust k and offset based on your specific sensor
    distance_cm = 27.0 / (ir_value / 1024.0) - 0.4
    return max(0, distance_cm)  # Ensure non-negative


# =========================
# MAIN LOOP
# =========================
loop_count = 0

while robot.step(timestep) != -1:
    loop_count += 1

    # ---------- READ SENSORS ----------
    gs0, gs1, gs2 = [s.getValue() for s in gs]
    ir_left = ir0.getValue()
    ir_right = ir1.getValue()

    # Calculate distances
    dist_left = calculate_distance_from_ir(ir_left)
    dist_right = calculate_distance_from_ir(ir_right)

    img = camera.getImage()
    if img:
        w = camera.getWidth()
        h = camera.getHeight()
        red_seen = red_in_center(img, w, h)
        blue_seen = blue_in_bottom(img, w, h)
    else:
        red_seen = False
        blue_seen = False

    # Receive distance information from supervisor (pedestrian and obstacle)
    sup_updated = False
    while sup_receiver.getQueueLength() > 0:
        raw = sup_receiver.getString()
        sup_receiver.nextPacket()
        try:
            t_str, ped_str, obs_str = raw.split(",")
            sup_time = float(t_str)
            sup_ped_distance = float(ped_str)
            sup_obs_distance = float(obs_str)
            sup_updated = True
        except ValueError:
            print(f"[{loop_count}] Warning: bad supervisor packet: {raw}")

    if sup_updated:
        ped_text = f"{sup_ped_distance:.3f} m" if sup_ped_distance is not None else "n/a"
        obs_text = f"{sup_obs_distance:.3f} m" if sup_obs_distance is not None else "n/a"
        status = f"\rPedestrian distance = {ped_text} | Obstacle distance = {obs_text}"
        # Throttle: only update when time advanced enough or distances changed significantly.
        ped_val = sup_ped_distance if sup_ped_distance is not None else last_ped_shown
        obs_val = sup_obs_distance if sup_obs_distance is not None else last_obs_shown
        time_ok = (sup_time is None) or (last_status_time < 0) or (sup_time - last_status_time >= STATUS_MIN_DT)
        ped_ok = (
            sup_ped_distance is not None
            and (last_ped_shown is None or abs(sup_ped_distance - last_ped_shown) >= STATUS_DELTA)
        )
        obs_ok = (
            sup_obs_distance is not None
            and (last_obs_shown is None or abs(sup_obs_distance - last_obs_shown) >= STATUS_DELTA)
        )
        if time_ok or ped_ok or obs_ok:
            last_status_time = sup_time if sup_time is not None else last_status_time
            last_ped_shown = sup_ped_distance if sup_ped_distance is not None else last_ped_shown
            last_obs_shown = sup_obs_distance if sup_obs_distance is not None else last_obs_shown
            print(status.ljust(90), end="", flush=True)
            status_line_active = True

    ped_close = (sup_ped_distance is not None) and (sup_ped_distance <= PED_STOP_DISTANCE)
    # Check if any ground sensor sees the line
    line_detected = (gs0 < LINE_THRESHOLD) or (gs1 < LINE_THRESHOLD) or (gs2 < LINE_THRESHOLD)
    ped_stop_condition = ped_close or (red_seen and sup_ped_distance is None)
    # ---------- RED LOGIC: STOP IMMEDIATELY ----------
    if ped_stop_condition:
        if status_line_active:
            print()
            status_line_active = False
        if not red_detected:
            print('Pedestrian DETECTED -> STOP')
            red_detected = True
        left_motor.setVelocity(0.0)
        right_motor.setVelocity(0.0)
        continue
    else:
        if red_detected:
            if status_line_active:
                print()
                status_line_active = False
            print('Red cleared -> resume')
        red_detected = False

    # ===================================================
    #    BLUE AVOIDANCE: CURVED ZIG-ZAG
    # ===================================================

    # Only treat blue as "avoid" when object is NEAR (blue + IR)
    blue_near = blue_seen and (ir_left > BLUE_NEAR_IR or ir_right > BLUE_NEAR_IR)

    # TRIGGER avoidance (only if not already in it)
    if blue_avoid_state is None and blue_near:
        blue_avoid_state = 'phase1_right_arc'
        blue_state_timer = 0
        print('Obstacle detected -> avoidance started')

    # If we are in any avoidance phase, override normal line following
    if blue_avoid_state is not None:
        blue_state_timer += 1

        # --- PHASE 1: slight RIGHT arc (move away from obstacle) ---
        if blue_avoid_state == 'phase1_right_arc':
            ls = ARC_FAST   # left wheel faster
            rs = ARC_SLOW   # right wheel slower

            if blue_state_timer >= PHASE1_DURATION:
                blue_avoid_state = 'phase2_left_arc'
                blue_state_timer = 0

        # --- PHASE 2: long LEFT arc (go around obstacle) ---
        elif blue_avoid_state == 'phase2_left_arc':
            ls = ARC_SLOW   # left wheel slower
            rs = ARC_FAST   # right wheel faster

            if blue_state_timer >= PHASE2_DURATION:
                blue_avoid_state = 'phase3_left_find_line'
                blue_state_timer = 0

        # --- PHASE 3: LEFT arc until line is found or timeout ---
        elif blue_avoid_state == 'phase3_left_find_line':
            ls = ARC_SLOW
            rs = ARC_FAST

            if line_detected:
                print(
                    f"[{loop_count}] LINE FOUND -> Exit avoidance "
                    f"(GS: L={gs0:.0f} C={gs1:.0f} R={gs2:.0f})"
                )
                blue_avoid_state = None
                blue_state_timer = 0
            elif blue_state_timer >= PHASE3_MAX:
                print(f"[{loop_count}] TIMEOUT -> Exit anyway")
                blue_avoid_state = None
                blue_state_timer = 0

        # Apply motor speeds during avoidance
        left_motor.setVelocity(min(ls, MAX_SPEED))
        right_motor.setVelocity(min(rs, MAX_SPEED))
        continue

    # ===================================================
    #             NORMAL LINE FOLLOWING
    # ===================================================
    left_on_line = gs0 < LINE_THRESHOLD
    center_on_line = gs1 < LINE_THRESHOLD
    right_on_line = gs2 < LINE_THRESHOLD

    if center_on_line and not left_on_line and not right_on_line:
        ls = rs = BASE_SPEED
    elif left_on_line and not center_on_line:
        ls, rs = BASE_SPEED * 0.4, BASE_SPEED
    elif right_on_line and not center_on_line:
        ls, rs = BASE_SPEED, BASE_SPEED * 0.4
    elif not (left_on_line or center_on_line or right_on_line):
        # lost line -> rotate slowly to search
        ls, rs = BASE_SPEED * 0.3, -BASE_SPEED * 0.3
    else:
        ls = rs = BASE_SPEED

    left_motor.setVelocity(ls)
    right_motor.setVelocity(rs)
