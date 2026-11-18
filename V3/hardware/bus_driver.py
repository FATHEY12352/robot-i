"""
STS3215 Serial Bus Driver & Mock Loopback Transport Layer.

Provides thread-safe half-duplex UART communication for Feetech STS3215 bus servos at 1,000,000 baud 8N1:
- Reentrant bus locking (threading.RLock) holding the lock through entire TX-flush-RX cycles.
- Elimination of buffer race conditions and half-duplex collisions.
- Pre-send buffer flush (reset_input_buffer) and optional auto-detecting hardware echo suppression.
- Configurable response timeout (default 12-15 ms) for high-frequency control loops without dead bus starvation.
- Full-fidelity MockSerialBus simulating multi-servo STS3215 registers, 5-DOF fallback, and bus events.
"""

from __future__ import annotations

import logging
import struct
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

import serial

from .sts3215_protocol import (
    BROADCAST_ID,
    ERR_OVERLOAD,
    INST_ACTION,
    INST_PING,
    INST_READ,
    INST_REG_WRITE,
    INST_RESET,
    INST_SYNC_WRITE,
    INST_WRITE,
    PREAMBLE,
    REG_ACC,
    REG_ERROR_STATUS,
    REG_GOAL_POSITION,
    REG_GOAL_SPEED,
    REG_ID,
    REG_LOCK,
    REG_PRESENT_CURRENT,
    REG_PRESENT_LOAD,
    REG_PRESENT_POS,
    REG_PRESENT_SPEED,
    REG_PRESENT_TEMP,
    REG_PRESENT_VOLT,
    REG_TORQUE_ENABLE,
    build_action_packet,
    build_ping_packet,
    build_read_packet,
    build_reg_write_packet,
    build_reset_packet,
    build_sync_write_positions_packet,
    build_write_packet,
    compute_checksum,
    decode_error_status,
    le_to_u16,
    parse_response_packet,
    u16_to_le,
    validate_checksum,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Classes
# =============================================================================

class BusDriverError(Exception):
    """Base exception for all serial bus driver errors."""
    pass


class BusTimeoutError(BusDriverError):
    """Raised when a servo does not return a response within the timeout deadline."""
    pass


class BusChecksumError(BusDriverError):
    """Raised when a response packet fails STS3215 inverted checksum validation."""
    pass


class BusFramingError(BusDriverError):
    """Raised when framing bytes or preambles cannot be synchronized."""
    pass


# =============================================================================
# Simulated STS3215 Servo (Virtual Memory & Behavior)
# =============================================================================

class SimulatedSTS3215:
    """
    Virtual STS3215 servo with authentic 256-byte memory map.
    Maintains EEPROM (0x00-0x27) and SRAM (0x28-0xFF), simulating torque,
    magnetic encoder ticks (0-4095), EEPROM locking, and fault flags.
    """

    def __init__(self, servo_id: int, initial_pos: int = 2048, torque_enabled: bool = False):
        self.servo_id = servo_id
        self.registers = bytearray(256)
        self.buffered_writes: Dict[int, bytearray] = {}
        self._lock = threading.Lock()

        # EEPROM Defaults
        self.registers[0x00] = 0x0C         # Model L
        self.registers[0x01] = 0x15         # Model H (0x150C = STS3215)
        self.registers[0x03] = 0x01         # Firmware Major
        self.registers[0x04] = 0x02         # Firmware Minor
        self.registers[REG_ID] = servo_id & 0xFF
        self.registers[0x06] = 0x00         # Baud 1M
        self.registers[0x07] = 0x00         # Return delay
        self.registers[0x08] = 0x01         # Response Level (1 = Read/Ping only)
        # Min/Max angle limits: 0 .. 4095
        struct.pack_into("<H", self.registers, 0x09, 0)
        struct.pack_into("<H", self.registers, 0x0B, 4095)
        self.registers[0x0D] = 80           # Max temp limit 80°C
        self.registers[0x0E] = 140          # Max volt limit 14.0V
        self.registers[0x0F] = 40           # Min volt limit 4.0V
        struct.pack_into("<H", self.registers, 0x10, 1000)  # Max torque (100%)
        struct.pack_into("<H", self.registers, 0x1F, 85)    # Zero offset

        # SRAM Defaults
        self.registers[REG_TORQUE_ENABLE] = 1 if torque_enabled else 0
        self.registers[REG_ACC] = 0
        struct.pack_into("<H", self.registers, REG_GOAL_POSITION, initial_pos)
        struct.pack_into("<H", self.registers, 0x2C, 0)     # Goal time
        struct.pack_into("<H", self.registers, REG_GOAL_SPEED, 0)
        self.registers[REG_LOCK] = 1        # EEPROM Locked by default
        struct.pack_into("<H", self.registers, REG_PRESENT_POS, initial_pos)
        struct.pack_into("<H", self.registers, REG_PRESENT_SPEED, 0)
        struct.pack_into("<H", self.registers, REG_PRESENT_LOAD, 0)
        self.registers[REG_PRESENT_VOLT] = 122   # 12.2V
        self.registers[REG_PRESENT_TEMP] = 34    # 34°C
        self.registers[REG_ERROR_STATUS] = 0
        self.registers[0x42] = 0            # Moving = 0
        struct.pack_into("<H", self.registers, REG_PRESENT_CURRENT, 120)  # 120 mA

    @property
    def present_pos(self) -> int:
        with self._lock:
            return struct.unpack_from("<H", self.registers, REG_PRESENT_POS)[0]

    @present_pos.setter
    def present_pos(self, pos: int):
        with self._lock:
            struct.pack_into("<H", self.registers, REG_PRESENT_POS, max(0, min(4095, int(pos))))

    @property
    def goal_pos(self) -> int:
        with self._lock:
            return struct.unpack_from("<H", self.registers, REG_GOAL_POSITION)[0]

    def read_bytes(self, address: int, length: int) -> bytes:
        with self._lock:
            if address < 0 or address >= len(self.registers):
                return b""
            end = min(len(self.registers), address + length)
            return bytes(self.registers[address:end])

    def write_bytes(self, address: int, data: bytes):
        with self._lock:
            is_locked = bool(self.registers[REG_LOCK])
            for i, val in enumerate(data):
                reg = address + i
                if reg >= len(self.registers):
                    break
                # If writing to EEPROM (0x00-0x27) while locked, changes do not apply to permanent registers
                if reg <= 0x27 and is_locked and reg != REG_LOCK:
                    continue
                self.registers[reg] = val

            # If writing to REG_GOAL_POSITION and torque is enabled, present position tracks goal position
            if address <= REG_GOAL_POSITION <= address + len(data) - 1:
                goal = struct.unpack_from("<H", self.registers, REG_GOAL_POSITION)[0]
                if self.registers[REG_TORQUE_ENABLE] == 1:
                    struct.pack_into("<H", self.registers, REG_PRESENT_POS, goal)

    def buffer_reg_write(self, address: int, data: bytes):
        with self._lock:
            self.buffered_writes[address] = bytearray(data)

    def execute_action(self):
        with self._lock:
            for addr, data in self.buffered_writes.items():
                self.write_bytes(addr, bytes(data))
            self.buffered_writes.clear()


# =============================================================================
# Mock Serial Bus (Loopback Transport Simulator)
# =============================================================================

class MockSerialBus:
    """
    Drop-in duck-typed replacement for serial.Serial.
    Simulates half-duplex STS3215 communication with realistic packet timing,
    preamble parsing, active/offline servo isolation, and fault injection.
    """

    def __init__(
        self,
        port: str = "COM38",
        baudrate: int = 1000000,
        timeout: Optional[float] = 0.015,
        write_timeout: float = 1.0,
        active_ids: Optional[Iterable[int]] = None,
        echo_enabled: bool = False
    ):
        self.port = str(port)
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.is_open = True
        self.echo_enabled = echo_enabled
        self.packets_sent = 0

        # Servos collection (IDs 1..16 pre-instantiated)
        self.servos: Dict[int, SimulatedSTS3215] = {sid: SimulatedSTS3215(sid) for sid in range(1, 17)}
        if active_ids is not None:
            self.active_ids: Set[int] = set(active_ids)
        else:
            # Default to 5-DOF on COM38 (1..5) and 6-DOF on COM39 (1..6)
            if "38" in self.port:
                self.active_ids = {1, 2, 3, 4, 5}
            else:
                self.active_ids = {1, 2, 3, 4, 5, 6}

        self._rx_buffer = bytearray()
        self._tx_buffer = bytearray()
        self._lock = threading.Lock()

        # Fault injection controls
        self.corrupt_checksum = False
        self.drop_responses = False

    @property
    def in_waiting(self) -> int:
        with self._lock:
            return len(self._rx_buffer)

    def open(self):
        with self._lock:
            self.is_open = True

    def close(self):
        with self._lock:
            self.is_open = False
            self._rx_buffer.clear()
            self._tx_buffer.clear()

    def reset_input_buffer(self):
        with self._lock:
            self._rx_buffer.clear()

    def reset_output_buffer(self):
        with self._lock:
            self._tx_buffer.clear()

    def flush(self):
        pass

    def get_servo(self, servo_id: int) -> Optional[SimulatedSTS3215]:
        return self.servos.get(servo_id)

    def connect_servo(self, servo_id: int, initial_pos: int = 2048):
        """Simulate hotplugging a servo onto the serial bus."""
        with self._lock:
            if servo_id not in self.servos:
                self.servos[servo_id] = SimulatedSTS3215(servo_id, initial_pos=initial_pos)
            else:
                self.servos[servo_id].present_pos = initial_pos
            self.active_ids.add(servo_id)

    def disconnect_servo(self, servo_id: int):
        """Simulate unplugging or powering off a servo."""
        with self._lock:
            self.active_ids.discard(servo_id)

    def attach_servo(self, servo_id: int, initial_pos: int = 2048):
        self.connect_servo(servo_id, initial_pos)

    def detach_servo(self, servo_id: int):
        self.disconnect_servo(servo_id)

    def write(self, data: bytes) -> int:
        if not self.is_open:
            raise serial.SerialException(f"Port {self.port} is closed")

        with self._lock:
            self.packets_sent += 1
            if self.echo_enabled:
                self._rx_buffer.extend(data)

            self._tx_buffer.extend(data)
            self._process_tx_buffer()
            return len(data)

    def read(self, size: int = 1) -> bytes:
        if not self.is_open:
            raise serial.SerialException(f"Port {self.port} is closed")

        deadline = time.perf_counter() + (self.timeout if self.timeout is not None else 0.05)
        while True:
            with self._lock:
                if len(self._rx_buffer) >= size:
                    chunk = self._rx_buffer[:size]
                    self._rx_buffer = self._rx_buffer[size:]
                    return bytes(chunk)
                elif self._rx_buffer and time.perf_counter() >= deadline:
                    chunk = bytes(self._rx_buffer)
                    self._rx_buffer.clear()
                    return chunk

            if time.perf_counter() >= deadline:
                return b""
            time.sleep(0.0005)

    def _process_tx_buffer(self):
        """Parse incoming frames in TX buffer and generate servo responses."""
        while len(self._tx_buffer) >= 6:
            try:
                idx = self._tx_buffer.index(PREAMBLE)
            except ValueError:
                self._tx_buffer.clear()
                break

            if idx > 0:
                self._tx_buffer = self._tx_buffer[idx:]

            if len(self._tx_buffer) < 4:
                break

            target_id = self._tx_buffer[2]
            length = self._tx_buffer[3]
            total_len = length + 4

            if len(self._tx_buffer) < total_len:
                break  # Incomplete frame, wait for more bytes

            packet = bytes(self._tx_buffer[:total_len])
            self._tx_buffer = self._tx_buffer[total_len:]

            inst = packet[4]
            params = packet[5:-1]

            self._dispatch_instruction(target_id, inst, params)

    def _dispatch_instruction(self, target_id: int, inst: int, params: bytes):
        if self.drop_responses:
            return

        # 1. Handle Broadcast SYNC_WRITE (0xFE / 0x83)
        if target_id == BROADCAST_ID and inst == INST_SYNC_WRITE:
            if len(params) >= 2:
                start_addr = params[0]
                data_len = params[1]
                chunk_len = data_len + 1
                chunks = params[2:]
                for i in range(0, len(chunks), chunk_len):
                    chunk = chunks[i : i + chunk_len]
                    if len(chunk) == chunk_len:
                        sid = chunk[0]
                        data = chunk[1:]
                        if sid in self.active_ids and sid in self.servos:
                            self.servos[sid].write_bytes(start_addr, data)
            return  # Broadcast commands produce NO response frames on half-duplex line

        # 2. Check if addressed servo is responsive
        if target_id not in self.active_ids or target_id not in self.servos:
            return  # Non-responsive / unwired servo: silence on the wire

        servo = self.servos[target_id]

        if inst == INST_PING:
            err = servo.registers[REG_ERROR_STATUS]
            body = [target_id, 0x02, err]
            chk = compute_checksum(body) if not self.corrupt_checksum else 0x00
            self._rx_buffer.extend(PREAMBLE + bytes(body) + bytes([chk]))

        elif inst == INST_READ:
            if len(params) >= 2:
                addr = params[0]
                read_len = params[1]
                data = servo.read_bytes(addr, read_len)
                err = servo.registers[REG_ERROR_STATUS]
                body = [target_id, len(data) + 2, err] + list(data)
                chk = compute_checksum(body) if not self.corrupt_checksum else 0x00
                self._rx_buffer.extend(PREAMBLE + bytes(body) + bytes([chk]))

        elif inst == INST_WRITE:
            if len(params) >= 1:
                addr = params[0]
                data = params[1:]
                servo.write_bytes(addr, data)
                # Standard STS3215 with Return Level = 1 returns no ACK for WRITE,
                # but if requested or testing ACK, write responses can be enabled.

        elif inst == INST_REG_WRITE:
            if len(params) >= 1:
                addr = params[0]
                data = params[1:]
                servo.buffer_reg_write(addr, data)

        elif inst == INST_ACTION:
            servo.execute_action()

        elif inst == INST_RESET:
            servo.registers[REG_ERROR_STATUS] = 0
            err = servo.registers[REG_ERROR_STATUS]
            body = [target_id, 0x02, err]
            chk = compute_checksum(body)
            self._rx_buffer.extend(PREAMBLE + bytes(body) + bytes([chk]))


# =============================================================================
# Production Bus Driver Implementation
# =============================================================================

class BusDriver:
    """
    High-performance, thread-safe half-duplex serial driver for STS3215 servos.
    Encapsulates PySerial with reentrant bus locking, atomic transaction control,
    buffer flushing, streaming frame parsing, and hardware echo suppression.
    """

    def __init__(
        self,
        port: str = "COM38",
        baudrate: int = 1000000,
        timeout: float = 0.015,
        write_timeout: float = 1.0,
        custom_serial: Optional[Any] = None,
        enable_echo_cancellation: Optional[bool] = None,
        use_mock: bool = False
    ):
        self.port = str(port)
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self._lock = threading.RLock()
        self.echo_cancellation: Optional[bool] = enable_echo_cancellation
        self._is_open = False

        if custom_serial is not None:
            self.ser = custom_serial
            self._is_open = getattr(custom_serial, "is_open", True)
        elif use_mock or self.port.upper() == "MOCK":
            self.ser = MockSerialBus(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self._is_open = True
        else:
            self.ser = None

    def open(self) -> bool:
        """Open the serial port thread-safely."""
        with self._lock:
            if self.ser is not None and getattr(self.ser, "is_open", False):
                self._is_open = True
                return True

            try:
                if self.ser is None:
                    self.ser = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=self.timeout,
                        write_timeout=self.write_timeout
                    )
                else:
                    self.ser.open()

                self._is_open = True

                if self.echo_cancellation is None:
                    self._detect_echo()

                return True
            except Exception as e:
                logger.error(f"Failed to open bus driver on {self.port}: {e}")
                self._is_open = False
                return False

    def connect(self) -> bool:
        """Alias for open() conforming to PROJECT.md interface."""
        return self.open()

    def close(self) -> None:
        """Close the serial port thread-safely."""
        with self._lock:
            if self.ser is not None and getattr(self.ser, "is_open", False):
                try:
                    self.ser.close()
                except Exception as e:
                    logger.debug(f"Error closing port {self.port}: {e}")
            self._is_open = False

    def disconnect(self) -> None:
        """Alias for close() conforming to PROJECT.md interface."""
        self.close()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if not self._is_open or self.ser is None:
                return False
            return bool(getattr(self.ser, "is_open", False))

    @property
    def is_connected(self) -> bool:
        """Alias for is_open."""
        return self.is_open

    @is_connected.setter
    def is_connected(self, value: bool):
        self._is_open = bool(value)

    # -------------------------------------------------------------------------
    # Auto Echo Detection
    # -------------------------------------------------------------------------

    def _detect_echo(self) -> None:
        """Probe the bus with a dummy packet to detect hardware TX-RX loopback."""
        try:
            test_packet = build_ping_packet(0xFD)
            self.ser.reset_input_buffer()
            self.ser.write(test_packet)
            self.ser.flush()
            time.sleep(0.002)

            in_w = getattr(self.ser, "in_waiting", 0)
            if in_w >= len(test_packet):
                read_back = self.ser.read(len(test_packet))
                self.echo_cancellation = (read_back == test_packet)
            else:
                self.echo_cancellation = False

            self.ser.reset_input_buffer()
        except Exception:
            self.echo_cancellation = False

    # -------------------------------------------------------------------------
    # Core Atomic Read / Write Transactions
    # -------------------------------------------------------------------------

    def transact_read(
        self,
        servo_id: int,
        address: int,
        length: int,
        timeout: Optional[float] = None
    ) -> Optional[bytes]:
        """
        Execute an atomic request-response transaction to read register bytes.
        Holds self._lock through write, echo absorption, and response parsing.
        """
        if length <= 0 or address < 0 or address > 255:
            return None

        packet = build_read_packet(servo_id, address, length)
        read_timeout = timeout if timeout is not None else self.timeout

        with self._lock:
            if not self.is_open:
                return None

            try:
                # 1. Clear any residual garbage
                self.ser.reset_input_buffer()

                # 2. Write command
                self.ser.write(packet)
                self.ser.flush()

                # 3. Discard echo if present
                if self.echo_cancellation:
                    self._read_exact(len(packet), timeout=0.005)

                # 4. Read response frame
                parsed = self._read_response_frame(servo_id, expected_data_len=length, timeout=read_timeout)
                if parsed and parsed.is_valid:
                    return parsed.data
                return None

            except (BusTimeoutError, BusChecksumError, BusFramingError):
                if self.ser:
                    self.ser.reset_input_buffer()
                return None
            except Exception as e:
                logger.debug(f"Exception during transact_read for servo {servo_id}: {e}")
                if self.ser:
                    self.ser.reset_input_buffer()
                return None

    def read_register(
        self,
        servo_id: int,
        address: int,
        length: int,
        timeout: Optional[float] = None
    ) -> Optional[bytes]:
        """Contract-conforming read_register method."""
        return self.transact_read(servo_id, address, length, timeout=timeout)

    def transact_write(
        self,
        servo_id: int,
        address: int,
        values: Union[bytes, bytearray, Sequence[int]],
        wait_settle: float = 0.0005
    ) -> bool:
        """
        Execute an atomic register write command under bus lock.
        """
        packet = build_write_packet(servo_id, address, values)

        with self._lock:
            if not self.is_open:
                return False

            try:
                self.ser.reset_input_buffer()
                self.ser.write(packet)
                self.ser.flush()

                if self.echo_cancellation:
                    self._read_exact(len(packet), timeout=0.005)

                if wait_settle > 0:
                    time.sleep(wait_settle)
                return True
            except Exception as e:
                logger.error(f"Error during transact_write for servo {servo_id}: {e}")
                return False

    def write_register(
        self,
        servo_id: int,
        address: int,
        values: Union[bytes, bytearray, Sequence[int]],
        wait_settle: float = 0.0005
    ) -> bool:
        """Contract-conforming write_register method."""
        return self.transact_write(servo_id, address, values, wait_settle=wait_settle)

    def send_ping(self, servo_id: int, timeout: Optional[float] = None) -> bool:
        """
        Ping a servo and verify status frame response under bus lock.
        """
        packet = build_ping_packet(servo_id)
        ping_timeout = timeout if timeout is not None else self.timeout

        with self._lock:
            if not self.is_open:
                return False

            try:
                self.ser.reset_input_buffer()
                self.ser.write(packet)
                self.ser.flush()

                if self.echo_cancellation:
                    self._read_exact(len(packet), timeout=0.005)

                parsed = self._read_response_frame(servo_id, expected_data_len=0, timeout=ping_timeout)
                return parsed is not None and parsed.is_valid
            except Exception:
                return False

    def sync_write_positions(
        self,
        targets: Dict[int, int],
        speed: int = 0,
        acc: int = 0,
        speeds: Optional[Dict[int, int]] = None,
        accs: Optional[Dict[int, int]] = None
    ) -> bool:
        """
        Broadcast goal positions to multiple servos in a single atomic frame.
        Guarantees zero half-duplex collisions because broadcast 0xFE produces no responses.
        """
        if not targets:
            return False

        # Support both scalar and per-servo speeds/accelerations
        resolved_speeds = speeds if speeds is not None else {sid: speed for sid in targets}
        resolved_accs = accs if accs is not None else {sid: acc for sid in targets}

        packet = build_sync_write_positions_packet(
            targets=targets,
            speeds=resolved_speeds,
            accs=resolved_accs,
            default_speed=speed,
            default_acc=acc,
            use_acc=True
        )

        with self._lock:
            if not self.is_open:
                return False

            try:
                self.ser.reset_input_buffer()
                self.ser.write(packet)
                self.ser.flush()

                if self.echo_cancellation:
                    self._read_exact(len(packet), timeout=0.005)

                return True
            except Exception as e:
                logger.error(f"Error during sync_write_positions: {e}")
                return False

    # -------------------------------------------------------------------------
    # Low-Level Streaming Response Parser
    # -------------------------------------------------------------------------

    def _read_exact(self, count: int, timeout: float) -> bytes:
        """Read exact byte count within timeout deadline."""
        buf = bytearray()
        deadline = time.perf_counter() + timeout
        while len(buf) < count:
            remaining = count - len(buf)
            chunk = self.ser.read(remaining)
            if chunk:
                buf.extend(chunk)
            elif time.perf_counter() >= deadline:
                break
            else:
                time.sleep(0.0002)
        return bytes(buf)

    def _read_response_frame(
        self,
        expected_id: int,
        expected_data_len: int,
        timeout: float
    ) -> Optional[Any]:
        """
        Streaming response frame parser.
        Finds preamble [0xFF, 0xFF], extracts ID and Length, receives full payload,
        and verifies checksum.
        """
        deadline = time.perf_counter() + timeout
        buf = bytearray()

        # Step 1: Scan for preamble 0xFF 0xFF
        while time.perf_counter() < deadline:
            b = self.ser.read(1)
            if not b:
                time.sleep(0.0002)
                continue
            buf.append(b[0])
            if len(buf) >= 2 and buf[-2:] == PREAMBLE:
                break
        else:
            raise BusTimeoutError(f"Preamble timeout awaiting response from servo {expected_id}")

        # Step 2: Read header (ID, Length) -> 2 bytes
        id_len = self._read_exact(2, timeout=max(0.003, deadline - time.perf_counter()))
        if len(id_len) < 2:
            raise BusTimeoutError(f"Header timeout awaiting response from servo {expected_id}")

        resp_id, length = id_len[0], id_len[1]
        if resp_id != expected_id:
            raise BusFramingError(f"Mismatched servo ID: expected {expected_id}, got {resp_id}")

        # Step 3: Read payload (ErrorStatus, Data[N], Checksum) -> length bytes
        payload = self._read_exact(length, timeout=max(0.005, deadline - time.perf_counter()))
        if len(payload) < length:
            raise BusTimeoutError(f"Incomplete payload for servo {expected_id}: expected {length}, got {len(payload)}")

        # Complete packet = PREAMBLE + [resp_id, length] + payload
        full_packet = PREAMBLE + bytes([resp_id, length]) + payload
        parsed = parse_response_packet(full_packet)
        if parsed is None or not parsed.is_valid:
            raise BusChecksumError(f"Checksum validation failed for servo {expected_id}")

        return parsed
