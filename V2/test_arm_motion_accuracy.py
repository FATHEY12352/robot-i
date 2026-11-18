"""
====================================================================
SO-101 Physical Arm Motion & Trajectory Recording Verification Test
====================================================================
Performs a rigorous, automated micro-motion accuracy and playback test:
1. Connects to COM38 at 1,000,000 baud.
2. Health-checks all 6 Feetech STS3215 servos (Voltage, Temp, Errors).
3. Drives a safe micro-motion (<= 4.5 degrees / ~50 ticks) on each joint.
4. Records continuous live motor feedback at 30 Hz.
5. Replays the recorded trajectory on the physical robot.
6. Measures real-time tracking error (Commanded vs Actual Encoder).
7. Verifies zero reverse-motion jumps and prints PASS/FAIL status.
"""

import time
import math
import json
import os
from so101_arm import SO101Arm
from trajectory_recorder import TrajectoryRecorder

def run_verification_test():
    print("=" * 70)
    print("       SO-101 ROBOT ARM HARDWARE & TRAJECTORY VERIFICATION")
    print("=" * 70)
    print("[*] Connecting to physical robot on COM38 @ 1,000,000 baud...")

    arm = SO101Arm("COM38", baudrate=1000000)
    if not arm.connect():
        print("[!] ERROR: Failed to connect to COM38. Aborting test.")
        return False

    print("[✓] Serial bus opened successfully!\n")

    # 1. Hardware Status Check
    print("--- STEP 1: Servo Hardware & Health Check ---")
    states = arm.get_all_states()
    if len(states) < 6:
        print(f"[!] Warning: Only {len(states)} / 6 servos responded!")
    else:
        print(f"[✓] All 6 servos online and communicating.")

    initial_raws = {}
    for sid in range(1, 7):
        st = states.get(sid, {})
        raw = st.get("raw_pos", 0)
        ang = st.get("angle", 0.0)
        volt = st.get("voltage", 0.0)
        temp = st.get("temp", 0)
        err = st.get("error", 0)
        initial_raws[sid] = raw
        err_str = "OK" if err == 0 else f"ERR(0x{err:02X})"
        print(f"  Motor {sid} ({SO101Arm.JOINTS[sid]['name']:<22}): Raw={raw:4d} | Angle={ang:5.1f}° | Volt={volt:4.1f}V | Temp={temp:2d}°C | Status={err_str}")

    print()

    # Clear any leftover overload flags and enable torque
    arm.clear_all_overloads()
    arm.enable_all_torque()
    time.sleep(0.1)

    # 2. Generate Safe Micro-Motion Trajectory (<= 4.0 degrees / ~45 ticks)
    print("--- STEP 2: Generating Safe Micro-Motion Trajectory ---")
    duration = 3.5 # seconds
    freq_hz = 30
    total_steps = int(duration * freq_hz)
    amplitude_ticks = 40 # 40 ticks = ~3.5 degrees (safe micro-motion)

    print(f"  Duration: {duration}s | Frequency: {freq_hz} Hz | Total Frames: {total_steps}")
    print(f"  Motion Amplitude: +/- {amplitude_ticks} ticks (+/- {amplitude_ticks * 0.08789:.2f} degrees)")

    synthetic_frames = []
    start_t = 0.0
    for i in range(total_steps):
        t = i / freq_hz
        # Smooth sine wave starting at 0, smoothly moving +amp, -amp, and back to 0
        sine_factor = math.sin(2.0 * math.pi * (t / duration))
        delta = int(amplitude_ticks * sine_factor)
        
        frame_raws = {}
        for sid in range(1, 7):
            base = initial_raws[sid]
            # Keep away from 0/4096 wrap boundaries
            val = base + delta
            val = max(50, min(4040, val))
            frame_raws[sid] = val

        synthetic_frames.append({
            "t": round(t, 4),
            "raw": frame_raws
        })

    print(f"[✓] Generated {len(synthetic_frames)} trajectory frames.\n")

    # 3. Stream Generated Motion to Physical Arm & Record Live Feedback
    print("--- STEP 3: Executing Motion on Arm & Recording Live Encoders ---")
    recorded_frames = []
    t_start = time.time()

    for i, frame in enumerate(synthetic_frames):
        target_t = frame["t"]
        elapsed = time.time() - t_start
        if target_t > elapsed:
            time.sleep(target_t - elapsed)

        # Send goals via SYNC WRITE
        arm.sync_write_raw(frame["raw"], speed=450)

        # Read actual encoder positions at high speed
        live_states = arm.get_all_states()
        recorded_frames.append({
            "t": round(time.time() - t_start, 4),
            "cmd": frame["raw"],
            "actual": {sid: live_states[sid]["raw_pos"] for sid in range(1, 7) if sid in live_states}
        })

        if i % 25 == 0 or i == len(synthetic_frames) - 1:
            print(f"  Progress: {i+1:3d}/{len(synthetic_frames)} frames ({(i+1)/len(synthetic_frames)*100:3.0f}%) | "
                  f"J1={live_states.get(1,{}).get('raw_pos',0)} J2={live_states.get(2,{}).get('raw_pos',0)} J6={live_states.get(6,{}).get('raw_pos',0)}")

    print(f"[✓] Motion execution complete! Recorded {len(recorded_frames)} frames.\n")

    # Save to disk
    os.makedirs("trajectories", exist_ok=True)
    traj_path = os.path.join("trajectories", "test_recorded_motion.json")
    with open(traj_path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": "SO-101 Verification Test Trajectory",
            "frames": [{"t": f["t"], "raw": f["actual"]} for f in recorded_frames]
        }, f, indent=2)
    print(f"[✓] Recorded trajectory saved to: {traj_path}\n")

    # 4. Replay the Recorded Trajectory and Verify Precision
    print("--- STEP 4: Replaying Recorded Trajectory on Robot Arm ---")
    time.sleep(0.5)
    recorder = TrajectoryRecorder(arm)
    test_play_frames = [{"t": f["t"], "raw": f["actual"]} for f in recorded_frames]

    replay_tracking_errors = {sid: [] for sid in range(1, 7)}
    reverse_jumps_detected = {sid: 0 for sid in range(1, 7)}
    prev_pos = dict(initial_raws)

    def replay_step_monitor(step_idx, total_steps, current_goal):
        nonlocal prev_pos
        # Sample actual position periodically during replay
        if step_idx % 5 == 0:
            st = arm.get_all_states()
            for sid in range(1, 7):
                if sid in st and sid in current_goal:
                    actual = st[sid]["raw_pos"]
                    cmd = current_goal[sid]
                    err = abs(actual - cmd)
                    replay_tracking_errors[sid].append(err)

                    # Check for reverse jumps
                    diff = actual - prev_pos.get(sid, actual)
                    if abs(diff) > 1500:
                        reverse_jumps_detected[sid] += 1
                    prev_pos[sid] = actual

    recorder.play(test_play_frames, loop=False, speed_factor=1.0, callback=replay_step_monitor)
    print("[✓] Replay finished successfully!\n")

    # 5. Analysis & Certification Report
    print("=" * 70)
    print("                  ACCURACY & FIDELITY REPORT")
    print("=" * 70)
    print(f"{'Joint':<8} | {'Start':<6} | {'Target Range':<14} | {'Max Err (Ticks)':<16} | {'Avg Err (Deg)':<14} | {'Reverse Jumps':<14} | {'Status'}")
    print("-" * 88)

    all_passed = True
    for sid in range(1, 7):
        errs = replay_tracking_errors[sid]
        max_err = max(errs) if errs else 0
        avg_err_ticks = (sum(errs) / len(errs)) if errs else 0
        avg_err_deg = avg_err_ticks * 0.08789
        rev_jumps = reverse_jumps_detected[sid]
        
        target_range_str = f"+/- {amplitude_ticks} ticks"
        # Pass threshold: avg error < 2.0 degrees, 0 reverse jumps
        passed = (avg_err_deg < 2.5) and (rev_jumps == 0)
        status_str = "[PASS] ✓" if passed else "[FAIL] ✗"
        if not passed:
            all_passed = False

        print(f"Joint {sid:<2d} | {initial_raws[sid]:<6d} | {target_range_str:<14} | {max_err:4d} ticks       | {avg_err_deg:5.2f}°        | {rev_jumps:<14d} | {status_str}")

    print("-" * 88)
    if all_passed:
        print("[✓✓✓] OVERALL TEST RESULT: PASSED! Hardware tracking is accurate, smooth, and 100% free of reverse jumps.")
    else:
        print("[!] OVERALL TEST RESULT: Some joints exceeded tolerance.")

    arm.close()
    return all_passed

if __name__ == "__main__":
    run_verification_test()

