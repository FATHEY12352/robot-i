import time
import serial
from so101_tester import SO101Controller, JOINT_NAMES

def quick_check():
    port = "COM38"
    print("=" * 60)
    print(f"=== SO-101 Fast Hardware Check on {port} ===")
    print("=" * 60)
    arm = SO101Controller(port=port, baudrate=1000000)
    if not arm.connect():
        print(f"[-] Error: Failed to connect to {port}")
        return

    print("Checking motor IDs 1 to 6...")
    found = []
    for sid in range(1, 7):
        name = JOINT_NAMES.get(sid, f"Joint {sid}")
        state = arm.get_joint_state(sid)
        if state:
            found.append(sid)
            print(f"  [+] ID {sid} ({name}):")
            print(f"      Angle: {state['angle_deg']} deg | Voltage: {state['voltage']}V | Temp: {state['temperature']}C")
        elif arm.ping(sid):
            found.append(sid)
            print(f"  [+] ID {sid} ({name}): Responsive (Ping OK)")
        else:
            print(f"  [-] ID {sid} ({name}): No response")

    print("-" * 60)
    print(f"Summary: {len(found)} / 6 motors responded: {found}")
    print("=" * 60)
    arm.close()

if __name__ == "__main__":
    quick_check()
