"""
====================================================================
SO-100 / SO-101 (SO-ARM100) Feetech STS3215 Core Control Library
====================================================================
Clean, high-level Python API to control the 6-DOF robot arm.
Provides smooth multi-joint trajectories, pose presets, gripper control,
and safety limits.
"""

import time
import serial
import threading
from typing import Dict, List, Optional, Tuple

class SO101Arm:
    TICKS_PER_REV = 4096.0
    DEG_TO_TICKS = 4096.0 / 360.0
    TICKS_TO_DEG = 360.0 / 4096.0

    # Joint Information
    JOINTS = {
        1: {"name": "Shoulder Pan (Base)", "min_deg": 0.0, "max_deg": 360.0, "default_speed": 400},
        2: {"name": "Shoulder Lift",        "min_deg": 0.0, "max_deg": 360.0, "default_speed": 400},
        3: {"name": "Elbow Flex",           "min_deg": 0.0, "max_deg": 360.0, "default_speed": 500},
        4: {"name": "Wrist Flex",           "min_deg": 0.0, "max_deg": 360.0, "default_speed": 600},
        5: {"name": "Wrist Roll",           "min_deg": 0.0, "max_deg": 360.0, "default_speed": 600},
        6: {"name": "Gripper",              "min_deg": 0.0, "max_deg": 360.0, "default_speed": 500},
    }

    # Registers (STS3215)
    REG_ID = 0x05
    REG_TORQUE_ENABLE = 0x28  # 40: 1=Enable, 0=Disable
    REG_GOAL_POSITION = 0x2A  # 42: 2 bytes
    REG_GOAL_TIME = 0x2C      # 44: 2 bytes
    REG_GOAL_SPEED = 0x2E     # 46: 2 bytes
    REG_LOCK = 0x37           # 55: 1=Locked, 0=Unlocked
    REG_PRESENT_POS = 0x38    # 56: 2 bytes
    REG_PRESENT_SPEED = 0x3A  # 58: 2 bytes
    REG_PRESENT_LOAD = 0x3C   # 60: 2 bytes
    REG_PRESENT_VOLT = 0x3E   # 62: 1 byte (0.1V)
    REG_PRESENT_TEMP = 0x3F   # 63: 1 byte (°C)

    INST_PING = 0x01
    INST_READ = 0x02
    INST_WRITE = 0x03
    INST_SYNC_WRITE = 0x83

    def __init__(self, port: str = "COM38", baudrate: int = 1000000, timeout: float = 0.04):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to the arm serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout, write_timeout=1.0)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[!] Connection failed on {self.port}: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Close serial connection."""
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
        self.is_connected = False

    def close(self):
        """Alias for disconnect."""
        self.disconnect()

    def center_joint_to_2048(self, servo_id: int) -> bool:
        """
        Calibrate servo so its current physical position becomes 2048 (half-turn).
        Places the 0/4096 seam 180 degrees away, completely eliminating wrap-around.
        """
        state = self.get_joint_state(servo_id)
        if not state:
            return False
        cur_raw = state["raw_pos"]
        # Disable torque on this servo
        self._write_reg(servo_id, self.REG_TORQUE_ENABLE, [0])
        time.sleep(0.02)
        # Unlock EEPROM
        self._write_reg(servo_id, self.REG_LOCK, [0])
        time.sleep(0.02)
        # Read current offset
        cur_off_b = self._read_reg(servo_id, 31, 2)
        cur_off = (cur_off_b[0] | (cur_off_b[1] << 8)) if cur_off_b else 85
        # Compute new offset: new_raw = cur_raw - (new_off - cur_off) == 2048
        # => new_off = cur_off + cur_raw - 2048
        delta = cur_raw - 2048
        new_off = (cur_off + delta) % 4096
        # Write new offset
        self._write_reg(servo_id, 31, [new_off & 0xFF, (new_off >> 8) & 0xFF])
        time.sleep(0.04)
        # Lock EEPROM
        self._write_reg(servo_id, self.REG_LOCK, [1])
        time.sleep(0.02)
        return True

    def center_all_servos(self) -> Dict[int, int]:
        """Center all 6 servos to 2048 at the current physical pose."""
        results = {}
        for sid in range(1, 7):
            success = self.center_joint_to_2048(sid)
            time.sleep(0.02)
            st = self.get_joint_state(sid)
            results[sid] = st["raw_pos"] if st else -1
        return results

    @staticmethod
    def _checksum(body: list) -> int:
        return (~sum(body)) & 0xFF

    def _write_reg(self, servo_id: int, addr: int, values: list):
        if not self.ser or not self.ser.is_open:
            return
        length = len(values) + 3
        body = [servo_id, length, self.INST_WRITE, addr] + values
        chk = self._checksum(body)
        pkt = bytes([0xFF, 0xFF] + body + [chk])
        with self.lock:
            try:
                self.ser.reset_input_buffer()
                self.ser.write(pkt)
            except Exception as e:
                pass
        time.sleep(0.001)

    def _read_reg(self, servo_id: int, addr: int, length: int, retries: int = 2) -> Optional[bytes]:
        if not self.ser or not self.ser.is_open:
            return None
        for _ in range(retries):
            body = [servo_id, 0x04, self.INST_READ, addr, length]
            chk = self._checksum(body)
            pkt = bytes([0xFF, 0xFF] + body + [chk])

            with self.lock:
                try:
                    self.ser.reset_input_buffer()
                    self.ser.write(pkt)
                except Exception:
                    continue

            t0 = time.time()
            buf = bytearray()
            while time.time() - t0 < self.timeout:
                with self.lock:
                    try:
                        if self.ser and self.ser.is_open and self.ser.in_waiting:
                            buf += self.ser.read(self.ser.in_waiting)
                    except Exception:
                        pass
                for i in range(len(buf)):
                    if buf[i] == servo_id and i + 1 < len(buf):
                        pkt_len = buf[i+1]
                        total = pkt_len + 2
                        if i + total <= len(buf):
                            cand = buf[i : i + total]
                            if self._checksum(cand[:-1]) == cand[-1]:
                                return bytes(cand[3:-1])
                time.sleep(0.001)
        return None

    # -------------------------------------------------------------
    # High-level Feedback Methods
    # -------------------------------------------------------------
    def get_joint_state(self, servo_id: int) -> Optional[Dict]:
        """Read live position, torque/load, current, voltage, temperature, and errors."""
        data = self._read_reg(servo_id, self.REG_PRESENT_POS, 15)
        if data and len(data) >= 8:
            pos = int.from_bytes(data[0:2], 'little')
            speed = int.from_bytes(data[2:4], 'little', signed=True)
            raw_load = int.from_bytes(data[4:6], 'little', signed=True)
            load_pct = round(raw_load * 0.1, 1) # 0.1% units
            volt = round(data[6] / 10.0, 1)
            temp = data[7]
            err = data[9] if len(data) > 9 else 0
            curr_ma = int.from_bytes(data[13:15], 'little', signed=True) if len(data) >= 15 else 0
            angle = pos * self.TICKS_TO_DEG
            return {
                "id": servo_id,
                "angle": round(angle, 1),
                "raw_pos": pos,
                "speed": speed,
                "load": load_pct,
                "voltage": volt,
                "temperature": temp,
                "current_ma": curr_ma,
                "error": err
            }
        return None

    def get_firmware_versions(self) -> Dict[int, str]:
        """Read firmware version of all 6 motors."""
        versions = {}
        for sid in range(1, 7):
            data = self._read_reg(sid, 0, 2)
            if data and len(data) >= 2:
                versions[sid] = f"v{data[0]}.{data[1]}"
            else:
                versions[sid] = "Unknown"
        return versions

    def get_all_states(self) -> Dict[int, Dict]:
        """Read states of all 6 joints."""
        states = {}
        for sid in range(1, 7):
            s = self.get_joint_state(sid)
            if s:
                states[sid] = s
        return states

    def clear_overload(self, servo_id: int):
        """Clear overload protection state on a servo if tripped."""
        err_data = self._read_reg(servo_id, 0x41, 1)
        if err_data and (err_data[0] & 0x20):
            self._write_reg(servo_id, self.REG_TORQUE_ENABLE, [0])
            time.sleep(0.01)
            self._write_reg(servo_id, 0x41, [0])
            time.sleep(0.01)
            self._write_reg(servo_id, self.REG_TORQUE_ENABLE, [1])
            time.sleep(0.01)

    def clear_all_overloads(self):
        """Clear overload flags on all 6 servos."""
        for sid in range(1, 7):
            self.clear_overload(sid)

    def sync_write_raw(self, goals: Dict[int, int], speed: int = 500):
        """Send goal positions to all specified servos simultaneously in ONE atomic packet."""
        if not self.ser or not self.ser.is_open or not goals:
            return
        start_addr = self.REG_GOAL_POSITION # 0x2A
        data_len = 6 # Pos(2) + Time(2) + Speed(2)

        params = [start_addr, data_len]
        for sid in sorted(goals.keys()):
            raw_clamped = max(0, min(4095, int(goals[sid])))
            p_l = raw_clamped & 0xFF
            p_h = (raw_clamped >> 8) & 0xFF
            t_l = 0
            t_h = 0
            s_l = speed & 0xFF
            s_h = (speed >> 8) & 0xFF
            params.extend([int(sid), p_l, p_h, t_l, t_h, s_l, s_h])

        length = len(params) + 2
        body = [0xFE, length, self.INST_SYNC_WRITE] + params
        chk = self._checksum(body)
        pkt = bytes([0xFF, 0xFF] + body + [chk])

        with self.lock:
            try:
                self.ser.reset_input_buffer()
                self.ser.write(pkt)
            except Exception:
                pass

    # -------------------------------------------------------------
    # Torque Control
    # -------------------------------------------------------------
    def set_torque(self, servo_id: int, enable: bool):
        """Enable (lock) or disable (free) torque for a joint."""
        self._write_reg(servo_id, self.REG_TORQUE_ENABLE, [1 if enable else 0])

    def enable_all_torque(self):
        """Lock all 6 joints in position, clearing any tripped overloads first."""
        self.clear_all_overloads()
        for sid in range(1, 7):
            self.set_torque(sid, True)

    def disable_all_torque(self):
        """Free all 6 joints (hand-teaching / gravity mode)."""
        for sid in range(1, 7):
            self.set_torque(sid, False)

    # -------------------------------------------------------------
    # Motion Control
    # -------------------------------------------------------------
    def move_joint_raw(self, servo_id: int, ticks: int, speed: int = 500):
        """Move a joint by raw ticks (0 to 4095)."""
        ticks = max(0, min(4095, int(ticks)))
        pos_b = list(ticks.to_bytes(2, 'little'))
        time_b = [0, 0]
        spd_b = list(int(speed).to_bytes(2, 'little'))
        self._write_reg(servo_id, self.REG_GOAL_POSITION, pos_b + time_b + spd_b)

    def move_joint(self, servo_id: int, angle_deg: float, speed: int = 500):
        """Move a joint to a specific angle in degrees (0.0 to 360.0)."""
        ticks = int(angle_deg * self.DEG_TO_TICKS)
        self.move_joint_raw(servo_id, ticks, speed)

    def move_joint_rel(self, servo_id: int, delta_deg: float, speed: int = 500) -> Optional[float]:
        """Move a joint relative to its current angle (+- degrees)."""
        state = self.get_joint_state(servo_id)
        if not state:
            return None
        target_deg = state["angle"] + delta_deg
        target_deg = max(0.0, min(360.0, target_deg))
        self.move_joint(servo_id, target_deg, speed)
        return target_deg

    def move_pose(self, pose: Dict[int, float], speed: int = 400, wait: float = 0.0):
        """
        Move multiple joints simultaneously.
        pose format: {1: 180.0, 2: 150.0, 3: 200.0, ...}
        """
        for sid, angle in pose.items():
            self.move_joint(sid, angle, speed)
        if wait > 0:
            time.sleep(wait)

    def smooth_move_pose(self, target_pose: Dict[int, float], duration: float = 1.5, steps: int = 25):
        """
        Smoothly interpolate from current angles to target pose using linear/cosine steps.
        Avoids sudden jerks on robot joints.
        """
        current_states = self.get_all_states()
        start_angles = {}
        for sid in target_pose.keys():
            if sid in current_states:
                start_angles[sid] = current_states[sid]["angle"]
            else:
                start_angles[sid] = target_pose[sid]

        dt = duration / steps
        for step in range(1, steps + 1):
            t = step / steps
            interp_pose = {}
            for sid, target_ang in target_pose.items():
                start_ang = start_angles[sid]
                # Linear interpolation
                ang = start_ang + (target_ang - start_ang) * t
                interp_pose[sid] = ang
            self.move_pose(interp_pose, speed=600)
            time.sleep(dt)

    # -------------------------------------------------------------
    # Gripper Controls
    # -------------------------------------------------------------
    def open_gripper(self, speed: int = 500):
        """Open gripper fully."""
        self.move_joint(6, 120.0, speed)

    def close_gripper(self, speed: int = 500):
        """Close gripper."""
        self.move_joint(6, 45.0, speed)

    def set_gripper(self, percent: float, speed: int = 500):
        """Set gripper opening percentage (0% = fully closed, 100% = fully open)."""
        pct = max(0.0, min(100.0, percent))
        # Interpolate between 45 deg (closed) and 130 deg (open)
        angle = 45.0 + (pct / 100.0) * (130.0 - 45.0)
        self.move_joint(6, angle, speed)

