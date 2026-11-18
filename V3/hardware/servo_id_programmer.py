"""
====================================================================
Feetech STS3215 Servo ID Programmer & Scanner Tool
====================================================================
Easily scan, detect, and program new IDs into Feetech STS3215 serial bus servos.
"""

import sys
import time
import argparse
import serial
from typing import Optional, List, Dict

PORT = "COM38"
BAUD = 1000000

def checksum(body: list) -> int:
    return (~sum(body)) & 0xFF

def write_reg(ser: serial.Serial, servo_id: int, addr: int, values: list):
    length = len(values) + 3
    body = [servo_id, length, 0x03, addr] + values
    chk = checksum(body)
    ser.reset_input_buffer()
    ser.write(bytes([0xFF, 0xFF] + body + [chk]))
    time.sleep(0.005)

def read_reg(ser: serial.Serial, servo_id: int, addr: int, length: int, timeout: float = 0.04) -> Optional[bytes]:
    body = [servo_id, 0x04, 0x02, addr, length]
    chk = checksum(body)
    ser.reset_input_buffer()
    ser.write(bytes([0xFF, 0xFF] + body + [chk]))
    
    t0 = time.time()
    buf = bytearray()
    while time.time() - t0 < timeout:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
        for i in range(len(buf)):
            if buf[i] == servo_id and i + 1 < len(buf):
                pkt_len = buf[i+1]
                total = pkt_len + 2
                if i + total <= len(buf):
                    cand = buf[i : i + total]
                    if checksum(cand[:-1]) == cand[-1]:
                        return bytes(cand[3:-1])
        time.sleep(0.001)
    return None

def ping(ser: serial.Serial, servo_id: int) -> bool:
    body = [servo_id, 0x02, 0x01]
    chk = checksum(body)
    ser.reset_input_buffer()
    ser.write(bytes([0xFF, 0xFF] + body + [chk]))
    time.sleep(0.01)
    t0 = time.time()
    buf = bytearray()
    while time.time() - t0 < 0.03:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting)
        for i in range(len(buf)):
            if buf[i] == servo_id and i + 1 < len(buf):
                return True
        time.sleep(0.001)
    return False

def scan_all(ser: serial.Serial, max_id: int = 15) -> List[int]:
    print(f"[*] Scanning servo IDs 1 to {max_id} on {ser.port}...")
    found = []
    for sid in range(1, max_id + 1):
        data = read_reg(ser, sid, 56, 8, timeout=0.03)
        if data and len(data) >= 8:
            pos = int.from_bytes(data[0:2], 'little')
            volt = data[6] / 10.0
            temp = data[7]
            print(f"  [+] Found Servo ID {sid}: Pos={pos:4d} | Volt={volt:.1f}V | Temp={temp}°C")
            found.append(sid)
        else:
            # Fallback ping
            if ping(ser, sid):
                print(f"  [+] Found Servo ID {sid} (Ping response)")
                found.append(sid)
    return found

def change_servo_id(ser: serial.Serial, old_id: int, new_id: int) -> bool:
    print(f"\n[*] Attempting to change Servo ID from {old_id} to {new_id}...")
    
    # Verify old_id responds
    if not ping(ser, old_id) and not read_reg(ser, old_id, 56, 2):
        print(f"[!] Error: No servo responded on Old ID {old_id}!")
        return False

    # 1. Disable Torque
    write_reg(ser, old_id, 40, [0]) # Torque Enable = 0
    time.sleep(0.02)

    # 2. Unlock EEPROM
    write_reg(ser, old_id, 55, [0]) # Lock = 0
    time.sleep(0.02)

    # 3. Write New ID to Register 5
    write_reg(ser, old_id, 5, [new_id])
    time.sleep(0.05)

    # 4. Lock EEPROM on the NEW ID
    write_reg(ser, new_id, 55, [1]) # Lock = 1
    time.sleep(0.02)

    # 5. Verify the NEW ID responds
    time.sleep(0.05)
    test_read = read_reg(ser, new_id, 56, 2)
    if test_read or ping(ser, new_id):
        print(f"[✓✓✓] SUCCESS: Servo ID successfully changed to {new_id} and saved to EEPROM!")
        return True
    else:
        print(f"[!] Warning: Written command sent, but servo did not answer on new ID {new_id} immediately.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Feetech STS3215 Servo ID Programmer & Scanner Tool")
    parser.add_argument("--port", type=str, default=PORT, help=f"Serial COM port (default: {PORT})")
    parser.add_argument("--scan", action="store_true", help="Scan bus and list all responding servos")
    parser.add_argument("--from-id", type=int, default=None, dest="old_id", help="Old/Current servo ID to change")
    parser.add_argument("--to-id", type=int, default=None, dest="new_id", help="New servo ID to assign (1-253)")
    args = parser.parse_args()

    print("=" * 65)
    print("      FEETECH STS3215 SERVO ID PROGRAMMER & SCANNER")
    print("=" * 65)

    try:
        ser = serial.Serial(args.port, BAUD, timeout=0.04)
        print(f"[✓] Connected to {args.port} at {BAUD} baud.\n")
    except Exception as e:
        print(f"[!] Could not open serial port {args.port}: {e}")
        return

    try:
        # Non-interactive CLI Mode: Change ID directly
        if args.old_id is not None and args.new_id is not None:
            print(f"[*] Non-interactive command: Changing ID {args.old_id} -> {args.new_id}")
            change_servo_id(ser, args.old_id, args.new_id)
            print("\n[*] Verifying on bus:")
            scan_all(ser, max_id=10)
            return

        # Scan Mode
        if args.scan:
            scan_all(ser, max_id=15)
            return

        # Interactive Mode
        found = scan_all(ser, max_id=10)
        print(f"\n[i] Connected servos found: {found}")

        if not found:
            print("\n[!] No servos detected. Please check:")
            print("  1. 12V DC power is connected and turned ON.")
            print("  2. The 3-pin cable is plugged in firmly.")
            print("  3. The USB Type-C board is connected to COM38.")
            return

        print("\n" + "-" * 50)
        print("OPTIONS:")
        print("  1. Change a Servo ID")
        print("  2. Rescan IDs")
        print("  3. Exit")
        print("-" * 50)

        choice = input("Enter choice (1-3) [default: 1]: ").strip() or "1"

        if choice == "1":
            print("\n[IMPORTANT SAFETY RULE]")
            print("  If you are programming a brand-new motor (which ships as ID 1),")
            print("  connect ONLY that single new motor to the adapter board first!")
            print("  (Disconnect the rest of the arm temporarily so you don't overwrite")
            print("  existing motors that also have ID 1).\n")

            old_default = found[0] if len(found) == 1 else 1
            old_str = input(f"Enter Current/Old Servo ID [{old_default}]: ").strip()
            old_id = int(old_str) if old_str else old_default

            new_str = input("Enter New Servo ID (1-6): ").strip()
            if not new_str:
                print("[!] Aborted: No new ID provided.")
                return
            new_id = int(new_str)

            if new_id < 1 or new_id > 253:
                print("[!] Error: ID must be between 1 and 253.")
                return

            change_servo_id(ser, old_id, new_id)

            # Final verify
            print("\n[*] Final scan to verify:")
            scan_all(ser, max_id=10)

        elif choice == "2":
            scan_all(ser, max_id=15)

    finally:
        ser.close()
        print("\n[✓] Port closed.")

if __name__ == "__main__":
    main()
