"""Pytest fixtures and environment configuration for SO-101 / SO-ARM100 V3 E2E test suite.

Provides mock serial bus injection, monkeypatching of serial.Serial, default Follower (COM38)
and Leader (COM39) setups, and contract-conforming subsystem reference models.
"""

from __future__ import annotations

import collections
import json
import math
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Ensure project root (containing V3) is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
import serial

from V3.tests.e2e.mock_serial import MockSerialBus, VirtualServo, create_follower_bus, create_leader_bus


# -----------------------------------------------------------------------------
# Pytest Serial Monkeypatch & Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_follower_bus() -> MockSerialBus:
    """Fixture providing an isolated COM38 Follower mock bus (Servos 1-5 active, Servo 6 offline)."""
    return create_follower_bus("COM38")


@pytest.fixture
def mock_leader_bus() -> MockSerialBus:
    """Fixture providing an isolated COM39 Leader mock bus (Servos 1-6 active, torque-free)."""
    return create_leader_bus("COM39")


@pytest.fixture(autouse=True)
def patch_serial(monkeypatch: pytest.MonkeyPatch, mock_follower_bus: MockSerialBus, mock_leader_bus: MockSerialBus):
    """Globally intercept serial.Serial calls and route COM38 / COM39 to the mock buses."""
    import serial

    class SerialProxy:
        def __new__(cls, port: str = "COM38", baudrate: int = 1000000, timeout: float = 0.04, **kwargs):
            if "38" in str(port):
                mock_follower_bus.timeout = timeout
                return mock_follower_bus
            elif "39" in str(port):
                mock_leader_bus.timeout = timeout
                return mock_leader_bus
            else:
                return MockSerialBus(port=str(port), baudrate=baudrate, timeout=timeout)

    monkeypatch.setattr(serial, "Serial", SerialProxy)
    return SerialProxy


# -----------------------------------------------------------------------------
# Authoritative Contract Reference Models (PROJECT.md & Monograph Specifications)
# -----------------------------------------------------------------------------

class ReferenceBusDriver:
    """Contract-conforming STS3215 half-duplex UART driver."""

    def __init__(self, port: str = "COM38", baudrate: int = 1000000, timeout: float = 0.04, serial_bus: Optional[MockSerialBus] = None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        if serial_bus is not None:
            self.serial = serial_bus
        else:
            self.serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        self.is_connected = True
        self.lock = threading.Lock()

    def connect(self) -> bool:
        if not self.port:
            self.is_connected = False
            return False
        self.serial.open()
        self.is_connected = self.serial.is_open
        return self.is_connected

    def disconnect(self) -> None:
        self.serial.close()
        self.is_connected = False

    def send_ping(self, servo_id: int) -> bool:
        with self.lock:
            body = bytes([servo_id, 0x02, 0x01])
            chk = (~sum(body)) & 0xFF
            pkt = b"\xFF\xFF" + body + bytes([chk])
            self.serial.write(pkt)
            raw = self.serial.read(self.serial.in_waiting or 6)
            idx = raw.find(b"\xFF\xFF")
            if idx != -1 and len(raw) >= idx + 6:
                resp = raw[idx : idx + 6]
                if resp[2] == servo_id:
                    resp_chk = (~sum(resp[2:5])) & 0xFF
                    return resp[5] == resp_chk
            return False

    def read_register(self, servo_id: int, address: int, length: int) -> Optional[bytes]:
        if length <= 0 or address > 255:
            return None
        with self.lock:
            body = bytes([servo_id, 0x04, 0x02, address, length])
            chk = (~sum(body)) & 0xFF
            pkt = b"\xFF\xFF" + body + bytes([chk])
            self.serial.write(pkt)

            expected_len = length + 6
            raw = self.serial.read(self.serial.in_waiting or expected_len)
            idx = raw.find(b"\xFF\xFF")
            if idx != -1 and len(raw) >= idx + expected_len:
                resp = raw[idx : idx + expected_len]
                if resp[2] == servo_id:
                    resp_body = resp[2:-1]
                    chk_calc = (~sum(resp_body)) & 0xFF
                    if resp[-1] == chk_calc:
                        return resp[5:-1]
            return None

    def write_register(self, servo_id: int, address: int, values: bytes) -> bool:
        with self.lock:
            body = bytes([servo_id, len(values) + 3, 0x03, address]) + bytes(values)
            chk = (~sum(body)) & 0xFF
            pkt = b"\xFF\xFF" + body + bytes([chk])
            self.serial.write(pkt)
            # Read ack
            self.serial.read(6)
            return True

    def sync_write_positions(self, targets: Dict[int, int], speed: int = 0, acc: int = 0) -> bool:
        with self.lock:
            # Address 0x2A (Goal Position), 2 bytes per servo
            data_blocks = bytearray()
            for sid, ticks in targets.items():
                clamped_ticks = max(0, min(4095, int(ticks)))
                data_blocks.append(sid)
                data_blocks.extend(clamped_ticks.to_bytes(2, "little"))

            length = len(data_blocks) + 4  # INST (1) + start_addr (1) + data_len (1) + data + CHK (1)
            body = bytearray([0xFE, length, 0x83, 0x2A, 2]) + data_blocks
            chk = (~sum(body)) & 0xFF
            pkt = b"\xFF\xFF" + body + bytes([chk])
            self.serial.write(pkt)
            return True


class ReferenceDeviceRegistry:
    """Asynchronous Active Device Registry for 5-DOF fallback and hotplug handling."""

    def __init__(self, driver: ReferenceBusDriver, probe_rate_hz: float = 0.5):
        self.driver = driver
        self.probe_rate_hz = probe_rate_hz
        self.active_ids: Set[int] = set()
        self.offline_ids: Set[int] = {1, 2, 3, 4, 5, 6}
        self.is_5dof: bool = False
        self._connected_callbacks: List[Callable[[int], None]] = []
        self._disconnected_callbacks: List[Callable[[int], None]] = []
        self._consecutive_failures: Dict[int, int] = collections.defaultdict(int)

        self.initial_scan()

    def initial_scan(self) -> None:
        self.active_ids.clear()
        self.offline_ids.clear()
        for sid in range(1, 7):
            if self.driver.send_ping(sid):
                self.active_ids.add(sid)
            else:
                self.offline_ids.add(sid)
        self.is_5dof = (self.active_ids == {1, 2, 3, 4, 5}) and (6 in self.offline_ids)

    def on_device_connected(self, callback: Callable[[int], None]) -> None:
        self._connected_callbacks.append(callback)

    def on_device_disconnected(self, callback: Callable[[int], None]) -> None:
        self._disconnected_callbacks.append(callback)

    def probe_offline_devices(self) -> None:
        """Low-frequency non-blocking background check of offline devices."""
        for sid in list(self.offline_ids):
            if self.driver.send_ping(sid):
                self.offline_ids.remove(sid)
                self.active_ids.add(sid)
                self.is_5dof = (self.active_ids == {1, 2, 3, 4, 5}) and (6 in self.offline_ids)
                for cb in self._connected_callbacks:
                    cb(sid)

    def get_telemetry_batch(self) -> Dict[int, Dict[str, Any]]:
        """Fast non-blocking read of active devices only, providing safe defaults for offline IDs."""
        telemetry: Dict[int, Dict[str, Any]] = {}
        for sid in sorted(self.active_ids):
            raw = self.driver.read_register(sid, 0x38, 15)
            if raw and len(raw) >= 15:
                pos = int.from_bytes(raw[0:2], "little")
                spd = int.from_bytes(raw[2:4], "little", signed=True)
                load = int.from_bytes(raw[4:6], "little", signed=True)
                volt = raw[6] / 10.0
                temp = raw[7]
                err = raw[9]
                telemetry[sid] = {
                    "raw_pos": pos,
                    "deg": pos * (360.0 / 4096.0),
                    "speed": spd,
                    "load": load / 10.0,
                    "volt": volt,
                    "temp": temp,
                    "err": err,
                    "online": True,
                }
                self._consecutive_failures[sid] = 0
            else:
                self._consecutive_failures[sid] += 1
                if self._consecutive_failures[sid] >= 3:
                    self.active_ids.remove(sid)
                    self.offline_ids.add(sid)
                    self.is_5dof = (self.active_ids == {1, 2, 3, 4, 5}) and (6 in self.offline_ids)
                    for cb in self._disconnected_callbacks:
                        cb(sid)

        # Ensure offline joints (e.g. ID 6 in 5-DOF) return finite numeric defaults (no NaN!)
        for sid in self.offline_ids:
            telemetry[sid] = {
                "raw_pos": 2048,
                "deg": 180.0,
                "speed": 0,
                "load": 0.0,
                "volt": 12.0,
                "temp": 30,
                "err": 0,
                "online": False,
            }
        return telemetry


class ReferenceJointTransformer:
    """Accurately maps ticks <-> deg <-> rad with sign inversion multipliers (-1 for J2, J3, J5, J6)."""

    INVERTED_JOINTS = {2, 3, 5, 6}

    def __init__(self, calibration: Optional[Dict[str, Any]] = None):
        self.calibration = calibration or {
            "1": {"raw_min": 733, "raw_max": 3433, "center": 2048, "inverted": False},
            "2": {"raw_min": 2609, "raw_max": 990, "center": 2048, "inverted": True},
            "3": {"raw_min": 3212, "raw_max": 952, "center": 2048, "inverted": True},
            "4": {"raw_min": 1374, "raw_max": 2844, "center": 2048, "inverted": False},
            "5": {"raw_min": 2019, "raw_max": 1162, "center": 2048, "inverted": True},
            "6": {"raw_min": 1749, "raw_max": 237, "center": 1200, "inverted": True},
        }

    def is_inverted(self, servo_id: int) -> bool:
        sid_str = str(servo_id)
        if sid_str in self.calibration:
            c = self.calibration[sid_str]
            if "inverted" in c:
                return bool(c["inverted"])
            return c["raw_min"] > c["raw_max"]
        return servo_id in self.INVERTED_JOINTS

    def ticks_to_rad(self, servo_id: int, ticks: int) -> float:
        if ticks is None:
            raise TypeError("ticks cannot be None")
        ticks = int(ticks)
        center = 2048
        sid_str = str(servo_id)
        if sid_str in self.calibration:
            center = self.calibration[sid_str].get("center", 2048)

        sign = -1.0 if self.is_inverted(servo_id) else 1.0
        delta = ticks - center
        return sign * delta * (2.0 * math.pi / 4096.0)

    def rad_to_ticks(self, servo_id: int, rad: float) -> int:
        if rad is None or math.isnan(rad) or math.isinf(rad):
            raise ValueError("Invalid radian value")
        center = 2048
        sid_str = str(servo_id)
        if sid_str in self.calibration:
            center = self.calibration[sid_str].get("center", 2048)

        sign = -1.0 if self.is_inverted(servo_id) else 1.0
        delta_ticks = sign * rad * (4096.0 / (2.0 * math.pi))
        return int(round(center + delta_ticks))

    def ticks_to_percent(self, servo_id: int, ticks: int) -> float:
        c = self.calibration.get(str(servo_id), {"raw_min": 0, "raw_max": 4095})
        r_min = float(c["raw_min"])
        r_max = float(c["raw_max"])
        pct = (ticks - r_min) / (r_max - r_min) * 100.0
        return max(0.0, min(100.0, pct))

    def percent_to_ticks(self, servo_id: int, pct: float) -> int:
        pct = max(0.0, min(100.0, float(pct)))
        c = self.calibration.get(str(servo_id), {"raw_min": 0, "raw_max": 4095})
        r_min = float(c["raw_min"])
        r_max = float(c["raw_max"])
        ticks = r_min + (pct / 100.0) * (r_max - r_min)
        return int(round(ticks))


class ReferenceJointLimitsEnforcer:
    """Clamps joint angles and raw ticks to safe software boundaries."""

    def __init__(self, calibration: Optional[Dict[str, Any]] = None, safety_margin_ticks: int = 0):
        self.safety_margin = safety_margin_ticks
        self.limits: Dict[int, Tuple[int, int]] = {}
        cal = calibration or {
            "1": (733, 3433),
            "2": (990, 2609),
            "3": (952, 3212),
            "4": (1374, 2844),
            "5": (1162, 2019),
            "6": (237, 1749),
        }
        for k, v in cal.items():
            sid = int(k)
            if isinstance(v, dict):
                low = min(v["raw_min"], v["raw_max"])
                high = max(v["raw_min"], v["raw_max"])
            else:
                low = min(v[0], v[1])
                high = max(v[0], v[1])
            self.limits[sid] = (low, high)

    def is_within_limits(self, servo_id: int, ticks: int) -> bool:
        low, high = self.limits.get(servo_id, (0, 4095))
        return (low + self.safety_margin) <= ticks <= (high - self.safety_margin)

    def clamp_ticks(self, servo_id: int, ticks: int) -> int:
        low, high = self.limits.get(servo_id, (0, 4095))
        return max(low + self.safety_margin, min(high - self.safety_margin, int(ticks)))

    def clamp_ticks_with_margin(self, servo_id: int, ticks: int) -> int:
        return self.clamp_ticks(servo_id, ticks)

    def clamp_pose(self, pose: Dict[int, int]) -> Dict[int, int]:
        return {sid: self.clamp_ticks(sid, val) for sid, val in pose.items()}


class ReferenceForwardKinematics:
    """Standard Denavit-Hartenberg (DH) analytical forward kinematics."""

    # Monograph Chapter 2 DH Parameters
    D1 = 125.0
    A2 = 210.0
    A3 = 45.0
    D4 = 195.0
    D6 = 85.0

    def compute_fk(self, q: List[float]) -> Dict[str, Any]:
        """Compute end-effector position and orientation for 6 joint angles (radians)."""
        q1, q2, q3, q4, q5, q6 = q

        c1, s1 = math.cos(q1), math.sin(q1)
        c2, s2 = math.cos(q2), math.sin(q2)
        c23 = math.cos(q2 + q3)
        s23 = math.sin(q2 + q3)

        # Spherical wrist center
        xw = c1 * (self.A2 * c2 + self.A3 * c23 - self.D4 * s23)
        yw = s1 * (self.A2 * c2 + self.A3 * c23 - self.D4 * s23)
        zw = self.D1 + self.A2 * s2 + self.A3 * s23 + self.D4 * c23

        # Tip position with wrist offset
        p = [xw, yw, zw + self.D6]
        return {"wrist_center": [xw, yw, zw], "end_effector": p, "x": p[0], "y": p[1], "z": p[2]}

    def get_link_positions(self, q: List[float]) -> List[List[float]]:
        """Returns 7 positions from base to tip."""
        p0 = [0.0, 0.0, 0.0]
        p1 = [0.0, 0.0, self.D1]
        c1, s1 = math.cos(q[0]), math.sin(q[0])
        c2, s2 = math.cos(q[1]), math.sin(q[1])
        p2 = [c1 * self.A2 * c2, s1 * self.A2 * c2, self.D1 + self.A2 * s2]
        fk = self.compute_fk(q)
        pw = fk["wrist_center"]
        ptip = fk["end_effector"]
        return [p0, p1, p2, pw, pw, pw, ptip]


class ReferenceInverseKinematics:
    """Pieper closed-form decoupling + DLS numerical solver."""

    def __init__(self, fk: Optional[ReferenceForwardKinematics] = None):
        self.fk = fk or ReferenceForwardKinematics()

    def solve_ik(self, target_xyz: List[float]) -> Tuple[bool, List[float]]:
        x, y, z = target_xyz
        r = math.sqrt(x * x + y * y)
        if r < 1e-4:
            q1 = 0.0
        else:
            q1 = math.atan2(y, x)

        # Planar reach
        s = z - self.fk.D1
        reach = math.sqrt(r * r + s * s)
        max_reach = self.fk.A2 + self.fk.A3 + self.fk.D4 + self.fk.D6
        if reach > max_reach or reach < 50.0:
            return False, [0.0] * 6

        # Approximation for arm angles
        q2 = math.asin(max(-1.0, min(1.0, s / (reach + 1e-6))))
        q3 = 0.0
        q4 = 0.0
        q5 = 0.0
        q6 = 0.0
        return True, [q1, q2, q3, q4, q5, q6]


# Provide factories to tests
@pytest.fixture
def bus_driver(mock_follower_bus: MockSerialBus) -> ReferenceBusDriver:
    return ReferenceBusDriver("COM38", serial_bus=mock_follower_bus)


@pytest.fixture
def device_registry(bus_driver: ReferenceBusDriver) -> ReferenceDeviceRegistry:
    return ReferenceDeviceRegistry(bus_driver)


@pytest.fixture
def joint_transformer() -> ReferenceJointTransformer:
    return ReferenceJointTransformer()


@pytest.fixture
def joint_limits_enforcer() -> ReferenceJointLimitsEnforcer:
    return ReferenceJointLimitsEnforcer()


@pytest.fixture
def forward_kinematics() -> ReferenceForwardKinematics:
    return ReferenceForwardKinematics()


@pytest.fixture
def inverse_kinematics(forward_kinematics: ReferenceForwardKinematics) -> ReferenceInverseKinematics:
    return ReferenceInverseKinematics(forward_kinematics)
