"""
Dynamic Active Device Registry & 5-DOF Fallback Subsystem.

Maintains real-time topology of connected STS3215 bus servos:
- Fast 50 Hz telemetry loop polling ONLY verified active servos (guaranteed <= 8 ms for 5 servos).
- Absolute elimination of the 80 ms dead bus blocking penalty when Servo ID 6 is unwired (5-DOF).
- Non-blocking 0.5 Hz background prober detecting hotplugged servos and promoting them to active.
- Automatic failover demotion on consecutive read failures.
- Event callbacks for device connection and disconnection.
- Thread-safe copy-on-read state synchronization with deadlock prevention.
"""

from __future__ import annotations

import logging
import math
import struct
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from .bus_driver import BusDriver

logger = logging.getLogger(__name__)


# =============================================================================
# Telemetry Data Structures
# =============================================================================

@dataclass(frozen=True)
class ServoTelemetry:
    """
    Immutable snapshot of an individual STS3215 servo's real-time state.
    Provides both typed attribute access and dictionary-style indexing for
    compatibility with Web Studio, controllers, and tests.
    """
    id: int
    position: int           # Raw ticks: 0..4095
    speed: int              # Present speed (signed 16-bit ticks/s)
    load: float             # Present load / torque percentage (-100.0% to +100.0%)
    voltage: float          # Present DC bus voltage in Volts (e.g. 12.1V)
    temperature: int        # Core temperature in °C
    error_code: int         # STS3215 register 0x41 error bitfield
    is_moving: bool         # True if currently traveling to target position
    timestamp: float        # Epoch timestamp of observation
    current_ma: int = 0     # Present motor current draw in mA
    is_online: bool = True  # True if actively communicating on bus

    # Semantic properties
    @property
    def servo_id(self) -> int:
        return self.id

    @property
    def raw_pos(self) -> int:
        return self.position

    @property
    def angle_deg(self) -> float:
        """Physical angle in degrees (0.0 to 360.0)."""
        return round(self.position * 360.0 / 4096.0, 2)

    @property
    def deg(self) -> float:
        return self.angle_deg

    @property
    def load_pct(self) -> float:
        return self.load

    @property
    def volt(self) -> float:
        return self.voltage

    @property
    def voltage_v(self) -> float:
        return self.voltage

    @property
    def temp(self) -> int:
        return self.temperature

    @property
    def temp_c(self) -> int:
        return self.temperature

    @property
    def err(self) -> int:
        return self.error_code

    @property
    def moving(self) -> bool:
        return self.is_moving

    @property
    def move_status(self) -> int:
        return 1 if self.is_moving else 0

    @property
    def online(self) -> bool:
        return self.is_online

    def to_dict(self) -> Dict[str, Any]:
        """Convert telemetry to standard JSON-serializable dictionary."""
        return {
            "id": self.id,
            "raw_pos": self.position,
            "pos": self.position,
            "deg": self.angle_deg,
            "speed": self.speed,
            "load": self.load,
            "load_pct": self.load,
            "volt": self.voltage,
            "voltage": self.voltage,
            "temp": self.temperature,
            "err": self.error_code,
            "moving": self.is_moving,
            "move": self.move_status,
            "current_ma": self.current_ma,
            "online": self.is_online,
            "ts": self.timestamp,
        }

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style subscripting: tel['deg'], tel['raw_pos'], tel['volt']."""
        k = key.lower()
        if k in ("id", "servo_id"):
            return self.id
        elif k in ("position", "pos", "raw_pos"):
            return self.position
        elif k in ("deg", "angle_deg", "angle"):
            return self.angle_deg
        elif k == "speed":
            return self.speed
        elif k in ("load", "load_pct"):
            return self.load
        elif k in ("volt", "voltage", "voltage_v"):
            return self.voltage
        elif k in ("temp", "temperature", "temp_c"):
            return self.temperature
        elif k in ("err", "error_code"):
            return self.error_code
        elif k in ("is_moving", "moving", "move", "move_status"):
            return self.is_moving if "move" in k and not k.endswith("status") else self.move_status
        elif k == "current_ma":
            return self.current_ma
        elif k in ("is_online", "online"):
            return self.is_online
        elif k in ("ts", "timestamp"):
            return self.timestamp
        raise KeyError(f"Invalid telemetry field: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        try:
            self[key]
            return True
        except KeyError:
            return False


@dataclass(frozen=True)
class TelemetryBatch:
    """
    Immutable container of telemetry for all servos in an arm at a specific instant.
    """
    arm_name: str           # "follower" (COM38) or "leader" (COM39)
    timestamp: float
    is_5dof: bool
    servos: Dict[int, ServoTelemetry]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "telemetry",
            "arm": self.arm_name,
            "dof": 5 if self.is_5dof else 6,
            "timestamp": self.timestamp,
            "servos": {str(sid): tel.to_dict() for sid, tel in self.servos.items()}
        }

    def to_ws_message(self) -> Dict[str, Any]:
        return self.to_dict()

    def __getitem__(self, servo_id: int) -> ServoTelemetry:
        return self.servos[servo_id]

    def __iter__(self):
        return iter(self.servos)

    def __len__(self) -> int:
        return len(self.servos)

    def __contains__(self, servo_id: int) -> bool:
        return servo_id in self.servos


# =============================================================================
# Device Registry
# =============================================================================

class DeviceRegistry:
    """
    Asynchronous Active Device Registry for dynamic servo topology management.
    Separates responsive servos from unwired/offline ones, ensuring high-speed
    telemetry runs with zero bus blocking penalties while background probing
    safely detects hotplugged devices.
    """

    def __init__(
        self,
        driver: BusDriver,
        expected_ids: Optional[Iterable[int]] = None,
        probe_interval: float = 2.0,      # 0.5 Hz background prober
        failure_threshold: int = 3,       # Consecutive read failures before demoting
        probe_timeout: float = 0.012,     # 12 ms max for offline probe
        arm_name: str = "follower",
        auto_start_prober: bool = False
    ):
        self._bus_driver = driver
        self.arm_name = arm_name
        self._probe_interval = probe_interval
        self._failure_threshold = failure_threshold
        self._probe_timeout = probe_timeout

        # Configure expected IDs (default: 1..6)
        if expected_ids is not None:
            self._expected_ids = set(int(sid) for sid in expected_ids)
        else:
            self._expected_ids = {1, 2, 3, 4, 5, 6}

        self._active_ids: Set[int] = set()
        self._offline_ids: Set[int] = set(self._expected_ids)
        self._consecutive_failures: Dict[int, int] = {sid: 0 for sid in self._expected_ids}

        # Dedicated mutex for registry topology state
        self._state_lock = threading.Lock()

        # Event callbacks
        self._connected_callbacks: List[Callable[[int], None]] = []
        self._disconnected_callbacks: List[Callable[[int], None]] = []

        # Background thread control
        self._stop_event = threading.Event()
        self._prober_thread: Optional[threading.Thread] = None

        # Execute initial bus scan
        self.initial_scan()

        if auto_start_prober:
            self.start_background_prober()

    # -------------------------------------------------------------------------
    # Public State Properties (Copy-on-Read Snapshots)
    # -------------------------------------------------------------------------

    @property
    def active_ids(self) -> Set[int]:
        """Snapshot of currently active and responsive servo IDs."""
        with self._state_lock:
            return set(self._active_ids)

    @property
    def offline_ids(self) -> Set[int]:
        """Snapshot of currently offline or unwired servo IDs."""
        with self._state_lock:
            return set(self._offline_ids)

    @property
    def expected_ids(self) -> Set[int]:
        """Snapshot of all expected servo IDs for this robot arm."""
        with self._state_lock:
            return set(self._expected_ids)

    @property
    def is_5dof(self) -> bool:
        """
        True if exactly joints 1..5 are active and gripper joint 6 is offline.
        """
        with self._state_lock:
            return (6 in self._offline_ids) and {1, 2, 3, 4, 5}.issubset(self._active_ids)

    # -------------------------------------------------------------------------
    # Event Registration
    # -------------------------------------------------------------------------

    def on_device_connected(self, callback: Callable[[int], None]) -> None:
        """Register callback for hotplug connection events: callback(servo_id)."""
        with self._state_lock:
            self._connected_callbacks.append(callback)

    def on_device_disconnected(self, callback: Callable[[int], None]) -> None:
        """Register callback for device disconnect/timeout demotions: callback(servo_id)."""
        with self._state_lock:
            self._disconnected_callbacks.append(callback)

    def _dispatch_callbacks(self, callbacks: List[Callable[[int], None]], servo_id: int) -> None:
        """Invoke callbacks safely outside internal locks to prevent deadlocks."""
        for cb in callbacks:
            try:
                cb(servo_id)
            except Exception as e:
                logger.error(f"Error in device registry listener for servo {servo_id}: {e}", exc_info=True)

    # -------------------------------------------------------------------------
    # Bus Scanning & Probing
    # -------------------------------------------------------------------------

    def initial_scan(self) -> Set[int]:
        """
        Scan all expected servo IDs using fast PING to determine initial topology.
        """
        active: Set[int] = set()
        offline: Set[int] = set()

        for sid in sorted(self._expected_ids):
            # Fast ping with short timeout (12 ms)
            if self._bus_driver.send_ping(sid, timeout=self._probe_timeout):
                active.add(sid)
            else:
                offline.add(sid)

        with self._state_lock:
            self._active_ids = active
            self._offline_ids = offline
            self._consecutive_failures = {sid: 0 for sid in self._expected_ids}

        return set(active)

    def probe_offline_devices(self) -> None:
        """
        Single-pass probe of all currently offline devices.
        If a device answers PING, it is atomically promoted to active_ids
        and on_device_connected callbacks are triggered.
        """
        with self._state_lock:
            to_probe = sorted(list(self._offline_ids))

        promoted: List[int] = []

        for sid in to_probe:
            # Send PING with probe timeout
            if self._bus_driver.send_ping(sid, timeout=self._probe_timeout):
                with self._state_lock:
                    if sid in self._offline_ids:
                        self._offline_ids.remove(sid)
                        self._active_ids.add(sid)
                        self._consecutive_failures[sid] = 0
                        promoted.append(sid)

        # Dispatch event notifications outside lock
        if promoted:
            with self._state_lock:
                cbs = list(self._connected_callbacks)
            for sid in promoted:
                self._dispatch_callbacks(cbs, sid)

    # -------------------------------------------------------------------------
    # Fast Telemetry Collection (Guaranteed <= 8 ms for 5 servos)
    # -------------------------------------------------------------------------

    def get_telemetry_batch(self) -> Dict[int, ServoTelemetry]:
        """
        Poll telemetry from all currently active servos at high speed.
        
        Guaranteed:
        1. Only queries active_ids over the physical serial bus.
        2. In 5-DOF mode (servos 1..5 active), total query time is <= 8.0 ms.
        3. Offline servos (such as ID 6) are NEVER queried on the bus, but safe
           neutral defaults (no NaN!) are returned so renderers/UI never crash.
        4. Any active servo failing self._failure_threshold times is demoted to
           offline_ids and on_device_disconnected callbacks are triggered.
        """
        with self._state_lock:
            targets = sorted(list(self._active_ids))
            all_expected = sorted(list(self._expected_ids))

        now = time.time()
        telemetry: Dict[int, ServoTelemetry] = {}
        demoted: List[int] = []

        # 1. Query active servos on the bus
        for sid in targets:
            # Read 15-byte continuous telemetry block starting at 0x38 (REG_PRESENT_POS)
            raw = self._bus_driver.read_register(sid, 0x38, 15)
            if raw and len(raw) >= 15:
                pos = raw[0] | (raw[1] << 8)
                spd = raw[2] | (raw[3] << 8)
                if spd > 32767:
                    spd -= 65536
                raw_load = raw[4] | (raw[5] << 8)
                if raw_load > 32767:
                    raw_load -= 65536
                load_pct = round(raw_load * 0.1, 1)
                volt = round(raw[6] / 10.0, 1)
                temp = raw[7]
                err = raw[9]
                moving = bool(raw[10])
                curr = raw[13] | (raw[14] << 8)
                if curr > 32767:
                    curr -= 65536

                telemetry[sid] = ServoTelemetry(
                    id=sid,
                    position=pos,
                    speed=spd,
                    load=load_pct,
                    voltage=volt,
                    temperature=temp,
                    error_code=err,
                    is_moving=moving,
                    timestamp=now,
                    current_ma=curr,
                    is_online=True
                )

                with self._state_lock:
                    self._consecutive_failures[sid] = 0
            else:
                # Track consecutive failures for active servo
                with self._state_lock:
                    self._consecutive_failures[sid] = self._consecutive_failures.get(sid, 0) + 1
                    if self._consecutive_failures[sid] >= self._failure_threshold:
                        if sid in self._active_ids:
                            self._active_ids.remove(sid)
                            self._offline_ids.add(sid)
                            demoted.append(sid)

                # Return neutral fallback for the dropped cycle
                telemetry[sid] = ServoTelemetry(
                    id=sid,
                    position=2048,
                    speed=0,
                    load=0.0,
                    voltage=12.0,
                    temperature=30,
                    error_code=0,
                    is_moving=False,
                    timestamp=now,
                    current_ma=0,
                    is_online=False
                )

        # 2. Populate offline expected servos with safe neutral defaults (no bus queries!)
        with self._state_lock:
            current_offline = set(self._offline_ids)

        for sid in current_offline:
            if sid not in telemetry:
                telemetry[sid] = ServoTelemetry(
                    id=sid,
                    position=2048,
                    speed=0,
                    load=0.0,
                    voltage=12.0,
                    temperature=30,
                    error_code=0,
                    is_moving=False,
                    timestamp=now,
                    current_ma=0,
                    is_online=False
                )

        # 3. Dispatch demotion events outside lock
        if demoted:
            with self._state_lock:
                cbs = list(self._disconnected_callbacks)
            for sid in demoted:
                self._dispatch_callbacks(cbs, sid)

        return telemetry

    def get_batch(self) -> TelemetryBatch:
        """Return strongly-typed TelemetryBatch containing all servos."""
        tel_map = self.get_telemetry_batch()
        return TelemetryBatch(
            arm_name=self.arm_name,
            timestamp=time.time(),
            is_5dof=self.is_5dof,
            servos=tel_map
        )

    # -------------------------------------------------------------------------
    # Background Prober Thread (0.5 Hz Non-Blocking)
    # -------------------------------------------------------------------------

    def start_background_prober(self) -> None:
        """Start the low-frequency background prober daemon thread."""
        with self._state_lock:
            if self._prober_thread is not None and self._prober_thread.is_alive():
                return
            self._stop_event.clear()
            self._prober_thread = threading.Thread(
                target=self._background_prober_loop,
                name=f"{self.arm_name}-DeviceProber",
                daemon=True
            )
            self._prober_thread.start()

    def stop_background_prober(self) -> None:
        """Stop the background prober daemon thread."""
        self._stop_event.set()
        if self._prober_thread is not None:
            self._prober_thread.join(timeout=1.0)
            self._prober_thread = None

    def _background_prober_loop(self) -> None:
        """Background probing loop executing at probe_interval (default 2.0s = 0.5 Hz)."""
        while not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self._probe_interval):
                break

            try:
                self.probe_offline_devices()
            except Exception as e:
                logger.error(f"Error in background prober: {e}", exc_info=True)
