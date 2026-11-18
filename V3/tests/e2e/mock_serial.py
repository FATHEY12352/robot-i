"""Virtual Mock Serial Bus & STS3215 Actuator Network Simulator.

Simulates half-duplex TTL UART bus physics, STS3215 binary framing, checksum verification,
256-byte register arrays, persistent EEPROM locking, and 5-DOF fallback dynamics (COM38 / COM39).
"""

from __future__ import annotations

import collections
import io
import math
import struct
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Union


class VirtualServo:
    """Accurately models a single Feetech STS3215 high-voltage bus servo.

    Maintains a 256-byte memory map (EEPROM 0x00-0x27, SRAM 0x28-0xFF),
    simulating holding torque, encoder ticks (0-4095), EEPROM locking,
    thermal model, and error flags.
    """

    # Instruction opcodes
    INST_PING = 0x01
    INST_READ = 0x02
    INST_WRITE = 0x03
    INST_REG_WRITE = 0x04
    INST_ACTION = 0x05
    INST_RESET = 0x06
    INST_SYNC_WRITE = 0x83

    # Register addresses
    REG_MODEL_L = 0x00
    REG_MODEL_H = 0x01
    REG_FW_VER_MAJ = 0x03
    REG_FW_VER_MIN = 0x04
    REG_ID = 0x05
    REG_BAUD = 0x06
    REG_RETURN_DELAY = 0x07
    REG_MIN_ANGLE = 0x09
    REG_MAX_ANGLE = 0x0B
    REG_MAX_TEMP = 0x0D
    REG_OFFSET = 0x1F
    REG_TORQUE_ENABLE = 0x28
    REG_ACC = 0x29
    REG_GOAL_POSITION = 0x2A
    REG_GOAL_TIME = 0x2C
    REG_GOAL_SPEED = 0x2E
    REG_LOCK = 0x37
    REG_PRESENT_POS = 0x38
    REG_PRESENT_SPEED = 0x3A
    REG_PRESENT_LOAD = 0x3C
    REG_PRESENT_VOLT = 0x3E
    REG_PRESENT_TEMP = 0x3F
    REG_ERROR_STATUS = 0x41
    REG_PRESENT_CURRENT = 0x45

    def __init__(self, servo_id: int, initial_pos: int = 2048, torque_enabled: bool = False):
        self.servo_id = servo_id
        self.registers = bytearray(256)
        self.buffered_writes: Dict[int, bytearray] = {}
        self.lock = threading.Lock()

        # Initialize default EEPROM registers
        self.registers[self.REG_MODEL_L] = 0x0C
        self.registers[self.REG_MODEL_H] = 0x15  # Model 0x150C (STS3215)
        self.registers[self.REG_FW_VER_MAJ] = 0x01
        self.registers[self.REG_FW_VER_MIN] = 0x02
        self.registers[self.REG_ID] = servo_id & 0xFF
        self.registers[self.REG_BAUD] = 0x00  # 1 Mbps
        self.registers[self.REG_RETURN_DELAY] = 0x00
        # Min/max angle limits: 0 .. 4095
        struct.pack_into("<H", self.registers, self.REG_MIN_ANGLE, 0)
        struct.pack_into("<H", self.registers, self.REG_MAX_ANGLE, 4095)
        self.registers[self.REG_MAX_TEMP] = 80  # 80°C threshold
        struct.pack_into("<H", self.registers, self.REG_OFFSET, 85)

        # Initialize SRAM registers
        self.registers[self.REG_TORQUE_ENABLE] = 1 if torque_enabled else 0
        self.registers[self.REG_ACC] = 0
        struct.pack_into("<H", self.registers, self.REG_GOAL_POSITION, initial_pos)
        struct.pack_into("<H", self.registers, self.REG_GOAL_TIME, 0)
        struct.pack_into("<H", self.registers, self.REG_GOAL_SPEED, 0)
        self.registers[self.REG_LOCK] = 1  # Locked by default
        struct.pack_into("<H", self.registers, self.REG_PRESENT_POS, initial_pos)
        struct.pack_into("<H", self.registers, self.REG_PRESENT_SPEED, 0)
        struct.pack_into("<H", self.registers, self.REG_PRESENT_LOAD, 0)
        self.registers[self.REG_PRESENT_VOLT] = 120  # 12.0 V (in 0.1V units)
        self.registers[self.REG_PRESENT_TEMP] = 32  # 32 °C
        self.registers[self.REG_ERROR_STATUS] = 0x00
        struct.pack_into("<H", self.registers, self.REG_PRESENT_CURRENT, 0)

        # Simulated physical position tracking
        self._current_pos: float = float(initial_pos)
        self._target_pos: float = float(initial_pos)

    @property
    def id(self) -> int:
        return self.registers[self.REG_ID]

    @id.setter
    def id(self, val: int) -> None:
        self.servo_id = val & 0xFF
        self.registers[self.REG_ID] = self.servo_id

    @property
    def present_pos(self) -> int:
        with self.lock:
            return struct.unpack_from("<H", self.registers, self.REG_PRESENT_POS)[0]

    @present_pos.setter
    def present_pos(self, val: int) -> None:
        val = max(0, min(4095, int(val)))
        with self.lock:
            self._current_pos = float(val)
            struct.pack_into("<H", self.registers, self.REG_PRESENT_POS, val)

    @property
    def goal_pos(self) -> int:
        with self.lock:
            return struct.unpack_from("<H", self.registers, self.REG_GOAL_POSITION)[0]

    def get_offset(self) -> int:
        with self.lock:
            return struct.unpack_from("<H", self.registers, self.REG_OFFSET)[0]

    def set_offset(self, offset: int) -> None:
        with self.lock:
            struct.pack_into("<H", self.registers, self.REG_OFFSET, offset & 0x0FFF)

    def write_registers(self, address: int, data: Union[bytes, bytearray, List[int]]) -> bool:
        """Write bytes to registers respecting EEPROM lock."""
        with self.lock:
            data_bytes = bytes(data)
            is_locked = bool(self.registers[self.REG_LOCK])

            # If writing to EEPROM space (< 0x28) while locked, reject write
            for i, b in enumerate(data_bytes):
                target_addr = address + i
                if target_addr >= len(self.registers):
                    break
                if target_addr < 0x28 and is_locked:
                    continue  # Ignore writes to locked EEPROM
                self.registers[target_addr] = b

                # Special side-effects
                if target_addr == self.REG_ID:
                    self.servo_id = b
                elif target_addr in (self.REG_GOAL_POSITION, self.REG_GOAL_POSITION + 1):
                    # Update target position and immediately track in mock
                    pos = struct.unpack_from("<H", self.registers, self.REG_GOAL_POSITION)[0]
                    self._target_pos = float(pos)
                    # When torque is enabled, present position tracks goal position
                    if self.registers[self.REG_TORQUE_ENABLE] != 0:
                        struct.pack_into("<H", self.registers, self.REG_PRESENT_POS, pos)
                        self._current_pos = float(pos)
                elif target_addr == self.REG_TORQUE_ENABLE and b != 0:
                    # Enabling torque locks target to current position
                    pos = struct.unpack_from("<H", self.registers, self.REG_PRESENT_POS)[0]
                    struct.pack_into("<H", self.registers, self.REG_GOAL_POSITION, pos)
                    self._target_pos = float(pos)
            return True

    def read_registers(self, address: int, length: int) -> bytes:
        """Read slice from 256-byte register array."""
        with self.lock:
            if address >= len(self.registers) or length <= 0:
                return b""
            end = min(len(self.registers), address + length)
            return bytes(self.registers[address:end])

    def center_to_2048(self) -> int:
        """Center current physical position to 2048 by updating offset register 31."""
        with self.lock:
            current_pos = struct.unpack_from("<H", self.registers, self.REG_PRESENT_POS)[0]
            current_offset = struct.unpack_from("<H", self.registers, self.REG_OFFSET)[0]
            new_offset = (current_offset + current_pos - 2048) % 4096
            struct.pack_into("<H", self.registers, self.REG_OFFSET, new_offset)
            struct.pack_into("<H", self.registers, self.REG_PRESENT_POS, 2048)
            self._current_pos = 2048.0
            self._target_pos = 2048.0
            return new_offset


class MockSerialBus:
    """Thread-safe virtual half-duplex TTL serial bus emulating STS3215 communication.

    Intercepts pyserial calls, maintains virtual servos on the bus, validates
    checksums, formats response frames, and simulates 5-DOF fallback on COM38.
    """

    def __init__(
        self,
        port: str = "COM38",
        baudrate: int = 1000000,
        timeout: float = 0.04,
        servos: Optional[Dict[int, VirtualServo]] = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = timeout
        self.is_open: bool = True

        self.rx_buffer = bytearray()
        self.tx_buffer = bytearray()
        self.last_written_bytes = b""
        self.lock = threading.RLock()

        # Virtual servos attached to this bus: ID -> VirtualServo
        self.servos: Dict[int, VirtualServo] = servos if servos is not None else {}
        self.offline_ids: Set[int] = set()

        # Fault injection flags
        self.corrupt_checksum_ids: Set[int] = set()
        self.drop_packet_ratio: float = 0.0
        self.injected_noise: bytearray = bytearray()
        self.latency_seconds: float = 0.0
        self.checksum_errors: int = 0
        self.packets_sent: int = 0
        self.packets_received: int = 0
        self.timeouts: int = 0

    @staticmethod
    def calc_checksum(body: Union[bytes, bytearray, List[int]]) -> int:
        """STS3215 Checksum: (~sum(body)) & 0xFF."""
        return (~sum(body)) & 0xFF

    def get_servo(self, servo_id: int) -> Optional[VirtualServo]:
        with self.lock:
            if servo_id in self.servos:
                return self.servos[servo_id]
            for s in list(self.servos.values()):
                if s.id == servo_id:
                    return s
            return None

    def add_servo(self, servo: VirtualServo) -> None:
        with self.lock:
            self.servos[servo.id] = servo
            self.offline_ids.discard(servo.id)

    def connect_servo(self, servo_id: int, initial_pos: int = 2048) -> None:
        """Hotplug a servo onto the virtual bus."""
        with self.lock:
            if servo_id not in self.servos:
                self.servos[servo_id] = VirtualServo(servo_id, initial_pos=initial_pos)
            self.offline_ids.discard(servo_id)

    def disconnect_servo(self, servo_id: int) -> None:
        """Physically disconnect a servo from the bus (5-DOF fallback simulation)."""
        with self.lock:
            self.offline_ids.add(servo_id)

    def is_servo_online(self, servo_id: int) -> bool:
        with self.lock:
            servo = self.get_servo(servo_id)
            if servo is None:
                return False
            return (servo.id not in self.offline_ids) and (servo_id not in self.offline_ids)

    def inject_noise_preamble(self, noise: bytes) -> None:
        with self.lock:
            self.injected_noise.extend(noise)

    def inject_corrupt_checksum(self, servo_id: int, enable: bool = True) -> None:
        with self.lock:
            if enable:
                self.corrupt_checksum_ids.add(servo_id)
            else:
                self.corrupt_checksum_ids.discard(servo_id)

    def inject_truncated_packet(self, partial: bytes) -> None:
        with self.lock:
            self.rx_buffer.extend(partial)

    # --- Pyserial API Emulation ---

    def open(self) -> None:
        with self.lock:
            self.is_open = True

    def close(self) -> None:
        with self.lock:
            self.is_open = False
            self.rx_buffer.clear()
            self.tx_buffer.clear()

    @property
    def in_waiting(self) -> int:
        with self.lock:
            return len(self.rx_buffer)

    def inWaiting(self) -> int:
        return self.in_waiting

    def reset_input_buffer(self) -> None:
        with self.lock:
            self.rx_buffer.clear()

    def reset_output_buffer(self) -> None:
        with self.lock:
            self.tx_buffer.clear()

    def flush(self) -> None:
        pass

    def write(self, data: bytes) -> int:
        """Simulate writing to UART line and processing incoming half-duplex packets."""
        with self.lock:
            if not self.is_open:
                raise IOError(f"Port {self.port} is closed")
            self.tx_buffer.extend(data)
            self.last_written_bytes = bytes(data)
            self.packets_sent += 1
            self._process_tx_stream()
            return len(data)

    def read(self, size: int = 1) -> bytes:
        """Simulate reading from UART line with timeout."""
        with self.lock:
            if not self.is_open:
                raise IOError(f"Port {self.port} is closed")
            if not self.rx_buffer:
                # If buffer is empty, simulate wait up to timeout
                if self.timeout and self.timeout > 0:
                    time.sleep(min(self.timeout, 0.005))
                return b""

            chunk = bytes(self.rx_buffer[:size])
            del self.rx_buffer[:size]
            return chunk

    def _process_tx_stream(self) -> None:
        """Scan tx_buffer for valid STS3215 request packets and generate responses."""
        buf = self.tx_buffer
        while len(buf) >= 6:
            # Look for 0xFF 0xFF header
            idx = buf.find(b"\xFF\xFF")
            if idx == -1:
                buf.clear()
                break
            if idx > 0:
                del buf[:idx]

            if len(buf) < 6:
                break

            target_id = buf[2]
            length = buf[3]
            total_packet_len = length + 4  # 2 header + 1 id + 1 len + body(length)

            if len(buf) < total_packet_len:
                break  # Incomplete packet, await more bytes

            packet = bytes(buf[:total_packet_len])
            del buf[:total_packet_len]

            body = packet[2:-1]
            chk = packet[-1]
            expected_chk = self.calc_checksum(body)

            if chk != expected_chk:
                self.checksum_errors += 1
                continue  # Discard corrupt packet

            # Process valid packet
            instruction = packet[4]
            params = packet[5:-1]
            self._dispatch_instruction(target_id, instruction, params)

    def _dispatch_instruction(self, target_id: int, inst: int, params: bytes) -> None:
        """Execute command and queue response in rx_buffer if unicast & online."""
        if self.latency_seconds > 0:
            time.sleep(self.latency_seconds)

        # Broadcast sync write (0xFE, 0x83)
        if target_id == 0xFE and inst == VirtualServo.INST_SYNC_WRITE:
            if len(params) >= 2:
                start_addr = params[0]
                data_len = params[1]
                offset = 2
                while offset + 1 + data_len <= len(params):
                    sid = params[offset]
                    servo_data = params[offset + 1 : offset + 1 + data_len]
                    offset += 1 + data_len
                    if self.is_servo_online(sid):
                        servo = self.servos[sid]
                        servo.write_registers(start_addr, servo_data)
            # Broadcast never returns a response packet on half-duplex bus
            return

        # Check if unicast target is online
        if not self.is_servo_online(target_id):
            # OFFLINE SERVO: No response generated (causes timeout on bus)
            self.timeouts += 1
            return

        servo = self.servos[target_id]
        err_byte = servo.registers[VirtualServo.REG_ERROR_STATUS]

        if inst == VirtualServo.INST_PING:
            self._queue_response(target_id, err_byte, b"")

        elif inst == VirtualServo.INST_READ:
            if len(params) >= 2:
                addr = params[0]
                length = params[1]
                data = servo.read_registers(addr, length)
                self._queue_response(target_id, err_byte, data)

        elif inst == VirtualServo.INST_WRITE:
            if len(params) >= 1:
                addr = params[0]
                data = params[1:]
                old_id = servo.id
                servo.write_registers(addr, data)
                if addr == VirtualServo.REG_ID and servo.id != old_id:
                    self.servos[servo.id] = servo
                    self.servos.pop(old_id, None)
                # On STS3215, write does not return data or returns standard ack
                self._queue_response(target_id, err_byte, b"")

        elif inst == VirtualServo.INST_REG_WRITE:
            if len(params) >= 1:
                addr = params[0]
                data = bytearray(params[1:])
                servo.buffered_writes[addr] = data
                self._queue_response(target_id, err_byte, b"")

        elif inst == VirtualServo.INST_ACTION:
            for addr, data in servo.buffered_writes.items():
                servo.write_registers(addr, data)
            servo.buffered_writes.clear()
            self._queue_response(target_id, err_byte, b"")

        elif inst == VirtualServo.INST_RESET:
            servo.__init__(target_id)
            self._queue_response(target_id, err_byte, b"")

    def _queue_response(self, servo_id: int, err_byte: int, data: bytes) -> None:
        """Build and append STS3215 response packet to rx_buffer."""
        # Prepend noise if injected
        if self.injected_noise:
            self.rx_buffer.extend(self.injected_noise)
            self.injected_noise.clear()

        length = len(data) + 2  # err_byte + chk
        body = [servo_id, length, err_byte] + list(data)
        chk = self.calc_checksum(body)

        # Checksum corruption injection
        if servo_id in self.corrupt_checksum_ids:
            chk = (chk ^ 0xFF) & 0xFF

        packet = bytes([0xFF, 0xFF, servo_id, length, err_byte]) + data + bytes([chk])
        self.rx_buffer.extend(packet)
        self.packets_received += 1

    def __enter__(self) -> MockSerialBus:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_follower_bus(port: str = "COM38") -> MockSerialBus:
    """Creates standard Follower arm mock bus (Servos 1-5 active, Servo 6 unwired/5-DOF)."""
    servos = {sid: VirtualServo(sid, initial_pos=2048, torque_enabled=True) for sid in range(1, 6)}
    # Add servo 6 as physically present in registry but marked offline
    bus = MockSerialBus(port=port, servos=servos)
    bus.disconnect_servo(6)
    return bus


def create_leader_bus(port: str = "COM39") -> MockSerialBus:
    """Creates standard Leader arm mock bus (Servos 1-6 active, torque-free hand teaching)."""
    servos = {sid: VirtualServo(sid, initial_pos=2048, torque_enabled=False) for sid in range(1, 7)}
    return MockSerialBus(port=port, servos=servos)
