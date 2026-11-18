"""
====================================================================
SO-100 / SO-101 (SO-ARM100) Real-Time Keyboard Teleoperation
====================================================================
Zero-latency keyboard jogging tool for Windows using msvcrt.
Control the arm joints in real-time directly from your terminal!

Controls:
  [A] / [D] : Joint 1 - Base Pan (Left / Right)
  [W] / [S] : Joint 2 - Shoulder Lift (Up / Down)
  [E] / [C] : Joint 3 - Elbow Flex (Up / Down)
  [R] / [F] : Joint 4 - Wrist Flex (Up / Down)
  [T] / [G] : Joint 5 - Wrist Roll (CW / CCW)
  [O] / [P] : Joint 6 - Gripper (Open / Close)

  [H]       : Go to Home Position (180 deg)
  [Space]   : Toggle Torque ON / OFF (Free movement)
  [+] / [-] : Change step size (1, 2, 5, 10 degrees)
  [Q]       : Quit
"""

import sys
import time
import msvcrt
from so101_arm import SO101Arm

def print_hud(arm, targets, step, torque_on):
    sys.stdout.write("\033[H\033[J") # Clear screen
    print("=" * 65)
    print("      SO-101 REAL-TIME KEYBOARD TELEOPERATION (JOG MODE)")
    print("=" * 65)
    t_status = "LOCKED (ON)" if torque_on else "FREE (OFF)"
    print(f"Torque: [{t_status}]   |   Step Size: [ {step:2.0f} deg ]   |   Port: COM38")
    print("-" * 65)
    print(f"{'Joint':<25} | {'Target Angle':<15} | {'Keys'}")
    print("-" * 65)
    print(f"J1: Base Pan (Yaw)        | {targets[1]:6.1f} deg     | [A] Left   / [D] Right")
    print(f"J2: Shoulder Lift (Pitch) | {targets[2]:6.1f} deg     | [W] Up     / [S] Down")
    print(f"J3: Elbow Flex (Pitch)    | {targets[3]:6.1f} deg     | [E] Up     / [C] Down")
    print(f"J4: Wrist Flex (Pitch)    | {targets[4]:6.1f} deg     | [R] Up     / [F] Down")
    print(f"J5: Wrist Roll            | {targets[5]:6.1f} deg     | [T] CW     / [G] CCW")
    print(f"J6: Gripper               | {targets[6]:6.1f} deg     | [O] Open   / [P] Close")
    print("-" * 65)
    print("Commands: [H] Home | [Space] Torque Toggle | [+] / [-] Step | [Q] Exit")
    print("=" * 65)
    sys.stdout.flush()

def main():
    arm = SO101Arm("COM38", baudrate=1000000)
    if not arm.connect():
        print("[!] Could not connect to COM38.")
        return

    print("[*] Connecting and reading current joint angles...")
    states = arm.get_all_states()
    targets = {}
    for sid in range(1, 7):
        if sid in states:
            targets[sid] = states[sid]["angle"]
        else:
            targets[sid] = 180.0

    step = 5.0
    torque_on = True
    arm.enable_all_torque()

    print_hud(arm, targets, step, torque_on)

    try:
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                # Handle special keys
                if ch in [b'\x00', b'\xe0']:
                    msvcrt.getch() # Skip arrow prefix
                    continue

                key = ch.decode('latin1', errors='ignore').lower()

                if key == 'q' or ch == b'\x1b': # Q or ESC
                    break

                # Step adjustment
                elif key == '+' or key == '=':
                    step = min(20.0, step + 1.0)
                elif key == '-' or key == '_':
                    step = max(1.0, step - 1.0)

                # Torque toggle
                elif key == ' ':
                    torque_on = not torque_on
                    if torque_on:
                        arm.enable_all_torque()
                    else:
                        arm.disable_all_torque()

                # Home position
                elif key == 'h':
                    targets = {1: 180.0, 2: 180.0, 3: 180.0, 4: 180.0, 5: 180.0, 6: 90.0}
                    arm.move_pose(targets, speed=400)

                # Joint 1: Base Pan
                elif key == 'a':
                    targets[1] = min(360.0, targets[1] + step)
                    arm.move_joint(1, targets[1], speed=500)
                elif key == 'd':
                    targets[1] = max(0.0, targets[1] - step)
                    arm.move_joint(1, targets[1], speed=500)

                # Joint 2: Shoulder Lift
                elif key == 'w':
                    targets[2] = min(360.0, targets[2] + step)
                    arm.move_joint(2, targets[2], speed=500)
                elif key == 's':
                    targets[2] = max(0.0, targets[2] - step)
                    arm.move_joint(2, targets[2], speed=500)

                # Joint 3: Elbow Flex
                elif key == 'e':
                    targets[3] = min(360.0, targets[3] + step)
                    arm.move_joint(3, targets[3], speed=500)
                elif key == 'c':
                    targets[3] = max(0.0, targets[3] - step)
                    arm.move_joint(3, targets[3], speed=500)

                # Joint 4: Wrist Flex
                elif key == 'r':
                    targets[4] = min(360.0, targets[4] + step)
                    arm.move_joint(4, targets[4], speed=600)
                elif key == 'f':
                    targets[4] = max(0.0, targets[4] - step)
                    arm.move_joint(4, targets[4], speed=600)

                # Joint 5: Wrist Roll
                elif key == 't':
                    targets[5] = min(360.0, targets[5] + step)
                    arm.move_joint(5, targets[5], speed=600)
                elif key == 'g':
                    targets[5] = max(0.0, targets[5] - step)
                    arm.move_joint(5, targets[5], speed=600)

                # Joint 6: Gripper
                elif key == 'o': # Open
                    targets[6] = min(130.0, targets[6] + step)
                    arm.move_joint(6, targets[6], speed=500)
                elif key == 'p': # Close
                    targets[6] = max(40.0, targets[6] - step)
                    arm.move_joint(6, targets[6], speed=500)

                print_hud(arm, targets, step, torque_on)

            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        arm.disconnect()
        print("\n[OK] Teleop session closed.")

if __name__ == "__main__":
    main()

