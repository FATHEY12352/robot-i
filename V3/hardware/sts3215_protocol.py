"""
STS3215 Bus Servo Binary Communication Protocol Specification & Codec.

Implements the official Feetech STS3215 serial protocol:
- Complete EEPROM (0x00 to 0x24) and SRAM (0x28 to 0x46) register definitions.
- Instruction opcodes (PING, READ, WRITE, REG_WRITE, ACTION, RESET, SYNC_READ, SYNC_WRITE).
- Inverted 8-bit checksum computation: (~sum(ID + Length + Instruction + Params)) & 0xFF.
- Little-endian 16-bit word serialization and deserialization.
- Frame encoders for unicast and broadcast packet construction.
- Response parser with dual 0xFF 0xFF preamble detection and error bitfield decoding.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

# =============================================================================
# Protocol Demarcation & Broadcast Identifiers
# =============================================================================

PREAMBLE: bytes = bytes([0xFF, 0xFF])
HEADER_BYTE: int = 0xFF
BROADCAST_ID: int = 0xFE

# =============================================================================
# Instruction Opcodes
# =============================================================================

INST_PING: int = 0x01
INST_READ: int = 0x02
INST_WRITE: int = 0x03
INST_REG_WRITE: int = 0x04
INST_ACTION: int = 0x05
INST_RESET: int = 0x06
INST_SYNC_READ: int = 0x82
INST_SYNC_WRITE: int = 0x83

# =============================================================================
# STS3215 EEPROM Register Map (0x00 – 0x24) [Non-Volatile, Retained Across Reboots]
# =============================================================================

REG_FIRMWARE_MAJOR: int = 0x00
REG_FIRMWARE_MINOR: int = 0x01
REG_SERVO_MODEL_L: int = 0x03
REG_SERVO_MODEL_H: int = 0x04
REG_ID: int = 0x05
REG_BAUD: int = 0x06
REG_BAUD_RATE: int = 0x06
REG_RETURN_DELAY: int = 0x07
REG_RESPONSE_LEVEL: int = 0x08
REG_MIN_ANGLE_LIMIT_L: int = 0x09
REG_MIN_ANGLE_LIMIT_H: int = 0x0A
REG_MIN_ANGLE_LIMIT: int = 0x09  # 16-bit word
REG_MAX_ANGLE_LIMIT_L: int = 0x0B
REG_MAX_ANGLE_LIMIT_H: int = 0x0C
REG_MAX_ANGLE_LIMIT: int = 0x0B  # 16-bit word
REG_MAX_TEMP_LIMIT: int = 0x0D
REG_MAX_VOLT_LIMIT: int = 0x0E
REG_MIN_VOLT_LIMIT: int = 0x0F
REG_MAX_TORQUE_L: int = 0x10
REG_MAX_TORQUE_H: int = 0x11
REG_MAX_TORQUE: int = 0x10  # 16-bit word
REG_PHASE: int = 0x12
REG_UNLOAD_CONDITION: int = 0x13
REG_LED_ALARM: int = 0x14
REG_PID_P: int = 0x15
REG_PID_D: int = 0x16
REG_PID_I: int = 0x17
REG_MIN_STARTUP_FORCE_L: int = 0x18
REG_MIN_STARTUP_FORCE_H: int = 0x19
REG_MIN_STARTUP_FORCE: int = 0x18  # 16-bit word
REG_CW_DEAD_ZONE: int = 0x1A
REG_CCW_DEAD_ZONE: int = 0x1B
REG_PROTECT_CURRENT_L: int = 0x1C
REG_PROTECT_CURRENT_H: int = 0x1D
REG_PROTECT_CURRENT: int = 0x1C  # 16-bit word
REG_ANGULAR_RESOLUTION: int = 0x1E
REG_OFFSET_L: int = 0x1F
REG_OFFSET_H: int = 0x20
REG_OFFSET: int = 0x1F  # 16-bit word
REG_MODE: int = 0x21
REG_PROTECT_TORQUE: int = 0x22
REG_PROTECT_TIME: int = 0x23
REG_OVERLOAD_TORQUE: int = 0x24

# =============================================================================
# STS3215 SRAM Register Map (0x28 – 0x46) [Volatile Fast Control & Telemetry]
# =============================================================================

REG_TORQUE_ENABLE: int = 0x28
REG_ACC: int = 0x29
REG_ACCELERATION: int = 0x29
REG_GOAL_POSITION_L: int = 0x2A
REG_GOAL_POSITION_H: int = 0x2B
REG_GOAL_POSITION: int = 0x2A  # 16-bit word
REG_GOAL_TIME_L: int = 0x2C
REG_GOAL_TIME_H: int = 0x2D
REG_GOAL_TIME: int = 0x2C  # 16-bit word
REG_GOAL_SPEED_L: int = 0x2E
REG_GOAL_SPEED_H: int = 0x2F
REG_GOAL_SPEED: int = 0x2E  # 16-bit word
REG_TORQUE_LIMIT_L: int = 0x30
REG_TORQUE_LIMIT_H: int = 0x31
REG_TORQUE_LIMIT: int = 0x30  # 16-bit word
REG_LOCK: int = 0x37
REG_PRESENT_POS_L: int = 0x38
REG_PRESENT_POS_H: int = 0x39
REG_PRESENT_POS: int = 0x38  # 16-bit word
REG_PRESENT_POSITION: int = 0x38
REG_PRESENT_SPEED_L: int = 0x3A
REG_PRESENT_SPEED_H: int = 0x3B
REG_PRESENT_SPEED: int = 0x3A  # 16-bit word
REG_PRESENT_LOAD_L: int = 0x3C
REG_PRESENT_LOAD_H: int = 0x3D
REG_PRESENT_LOAD: int = 0x3C  # 16-bit word
REG_PRESENT_VOLT: int = 0x3E
REG_PRESENT_VOLTAGE: int = 0x3E
REG_PRESENT_TEMP: int = 0x3F
REG_PRESENT_TEMPERATURE: int = 0x3F
REG_ASYNC_WRITE_FLAG: int = 0x40
REG_ERROR_STATUS: int = 0x41
REG_SERVO_STATUS: int = 0x41
REG_STATUS_ERROR: int = 0x41
REG_MOVE_STATUS: int = 0x42
REG_MOVING: int = 0x42
REG_PRESENT_CURRENT_L: int = 0x45
REG_PRESENT_CURRENT_H: int = 0x46
REG_PRESENT_CURRENT: int = 0x45  # 16-bit word

# =============================================================================
# Error Status Bitmask Definitions (Register 0x41 & Status Response Byte)
# =============================================================================

ERR_VOLTAGE: int = 0x01        # Bit 0: Voltage out of bounds (<4.0V or >14.0V)
ERR_SENSOR: int = 0x02         # Bit 1: Magnetic encoder reading missing / invalid
ERR_TEMPERATURE: int = 0x04    # Bit 2: Internal core temp >= 70°C
ERR_CURRENT: int = 0x08        # Bit 3: Motor current limit exceeded (>2.0A)
ERR_ANGLE_LIMIT: int = 0x10    # Bit 4: Target or present position outside limits
ERR_OVERLOAD: int = 0x20       # Bit 5: Stall torque exceeded continuously for >200ms
ERR_INSTRUCTION: int = 0x40    # Bit 6: Unknown opcode or invalid parameter length

ERROR_BIT_NAMES: Dict[str, int] = {
    "voltage_error": ERR_VOLTAGE,
    "sensor_error": ERR_SENSOR,
    "temperature_error": ERR_TEMPERATURE,
    "current_error": ERR_CURRENT,
    "angle_limit_error": ERR_ANGLE_LIMIT,
    "overload_error": ERR_OVERLOAD,
    "instruction_error": ERR_INSTRUCTION,
}

# =============================================================================
# Checksum Computation & Validation
# =============================================================================

def compute_checksum(body: Sequence[int]) -> int:
    """
    Compute STS3215 inverted 8-bit checksum.
    Formula: (~sum(ID + Length + Instruction + Params)) & 0xFF.
    """
    return (~sum(body)) & 0xFF


def validate_checksum(body_including_checksum: Sequence[int]) -> bool:
    """
    Validate an STS3215 frame body including its trailing checksum byte.
    In inverted checksum arithmetic: (sum(body[:-1]) + checksum) & 0xFF == 0xFF.
    """
    if len(body_including_checksum) < 2:
        return False
    body = body_including_checksum[:-1]
    expected = compute_checksum(body)
    return expected == body_including_checksum[-1]


# =============================================================================
# Little-Endian Word Serialization & Deserialization
# =============================================================================

def u16_to_le(value: int) -> bytes:
    """Pack an unsigned 16-bit integer (0..65535) into 2 Little-Endian bytes."""
    return struct.pack("<H", int(value) & 0xFFFF)


def s16_to_le(value: int) -> bytes:
    """Pack a signed 16-bit integer (-32768..32767) into 2 Little-Endian bytes."""
    clamped = max(-32768, min(32767, int(value)))
    return struct.pack("<h", clamped)


def le_to_u16(data: Union[bytes, bytearray, Sequence[int]], offset: int = 0) -> int:
    """Unpack 2 Little-Endian bytes starting at offset into an unsigned 16-bit integer."""
    buf = bytes(data[offset : offset + 2])
    if len(buf) < 2:
        raise ValueError(f"Insufficient bytes for u16: expected 2, got {len(buf)}")
    return struct.unpack_from("<H", buf, 0)[0]


def le_to_s16(data: Union[bytes, bytearray, Sequence[int]], offset: int = 0) -> int:
    """Unpack 2 Little-Endian bytes starting at offset into a signed 16-bit integer."""
    buf = bytes(data[offset : offset + 2])
    if len(buf) < 2:
        raise ValueError(f"Insufficient bytes for s16: expected 2, got {len(buf)}")
    return struct.unpack_from("<h", buf, 0)[0]


# =============================================================================
# Packet Builders
# =============================================================================

def build_ping_packet(servo_id: int) -> bytes:
    """
    Build a PING request frame.
    Format: [0xFF, 0xFF, ID, Length=2, INST_PING=0x01, Checksum]
    """
    body = [servo_id & 0xFF, 0x02, INST_PING]
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_read_packet(servo_id: int, address: int, length: int) -> bytes:
    """
    Build a READ request frame.
    Format: [0xFF, 0xFF, ID, Length=4, INST_READ=0x02, Address, LengthToRead, Checksum]
    """
    body = [servo_id & 0xFF, 0x04, INST_READ, address & 0xFF, length & 0xFF]
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_write_packet(servo_id: int, address: int, values: Union[bytes, bytearray, Sequence[int]]) -> bytes:
    """
    Build a WRITE command frame.
    Format: [0xFF, 0xFF, ID, Length=3+N, INST_WRITE=0x03, Address, Val0, ..., ValN, Checksum]
    """
    val_bytes = list(values)
    pkt_len = len(val_bytes) + 3
    body = [servo_id & 0xFF, pkt_len & 0xFF, INST_WRITE, address & 0xFF] + val_bytes
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_reg_write_packet(servo_id: int, address: int, values: Union[bytes, bytearray, Sequence[int]]) -> bytes:
    """
    Build an asynchronous buffered REG_WRITE command frame.
    Format: [0xFF, 0xFF, ID, Length=3+N, INST_REG_WRITE=0x04, Address, Val0, ..., ValN, Checksum]
    Payload is stored in servo SRAM buffer until an ACTION command is received.
    """
    val_bytes = list(values)
    pkt_len = len(val_bytes) + 3
    body = [servo_id & 0xFF, pkt_len & 0xFF, INST_REG_WRITE, address & 0xFF] + val_bytes
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_action_packet(servo_id: int = BROADCAST_ID) -> bytes:
    """
    Build an ACTION command frame triggering buffered REG_WRITE motions.
    Format: [0xFF, 0xFF, ID, Length=2, INST_ACTION=0x05, Checksum]
    """
    body = [servo_id & 0xFF, 0x02, INST_ACTION]
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_reset_packet(servo_id: int) -> bytes:
    """
    Build a RESET command frame restoring runtime counters without corrupting EEPROM.
    Format: [0xFF, 0xFF, ID, Length=2, INST_RESET=0x06, Checksum]
    """
    body = [servo_id & 0xFF, 0x02, INST_RESET]
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_sync_write_packet(
    start_address: int,
    data_len_per_servo: int,
    servo_data: Union[Dict[int, Sequence[int]], Sequence[Tuple[int, Sequence[int]]]]
) -> bytes:
    """
    Build a generic broadcast SYNC_WRITE packet.
    Format:
      [0xFF, 0xFF, 0xFE, Length, 0x83, StartAddr, DataLen,
       ID1, Data1_0, ..., Data1_N, ID2, Data2_0, ..., Data2_N, ..., Checksum]
    """
    if isinstance(servo_data, dict):
        items = sorted(servo_data.items(), key=lambda x: x[0])
    else:
        items = list(servo_data)

    params: List[int] = [start_address & 0xFF, data_len_per_servo & 0xFF]
    for sid, data in items:
        params.append(sid & 0xFF)
        data_list = list(data)
        if len(data_list) != data_len_per_servo:
            raise ValueError(
                f"Data length mismatch for servo {sid}: expected {data_len_per_servo}, got {len(data_list)}"
            )
        params.extend([b & 0xFF for b in data_list])

    length = len(params) + 2
    body = [BROADCAST_ID, length & 0xFF, INST_SYNC_WRITE] + params
    chk = compute_checksum(body)
    return PREAMBLE + bytes(body) + bytes([chk])


def build_sync_write_positions_packet(
    targets: Dict[int, int],
    speeds: Optional[Dict[int, int]] = None,
    accs: Optional[Dict[int, int]] = None,
    default_speed: int = 0,
    default_acc: int = 0,
    use_acc: bool = True
) -> bytes:
    """
    Build an atomic broadcast SYNC_WRITE packet commanding target positions to multiple servos.
    
    If use_acc is True (standard high-precision control starting at REG_ACC 0x29):
      data_len = 7 bytes per servo: [ACC (1), Pos_L (1), Pos_H (1), Time_L (1), Time_H (1), Spd_L (1), Spd_H (1)]
    If use_acc is False (starting at REG_GOAL_POSITION 0x2A):
      data_len = 6 bytes per servo: [Pos_L (1), Pos_H (1), Time_L (1), Time_H (1), Spd_L (1), Spd_H (1)]
    """
    if not targets:
        raise ValueError("Target servo position dictionary cannot be empty")

    servo_chunks: Dict[int, List[int]] = {}
    for sid in sorted(targets.keys()):
        raw_pos = max(0, min(4095, int(targets[sid])))
        speed_val = default_speed if speeds is None or sid not in speeds else max(0, min(4095, int(speeds[sid])))
        acc_val = default_acc if accs is None or sid not in accs else max(0, min(254, int(accs[sid])))

        pos_bytes = u16_to_le(raw_pos)
        time_bytes = u16_to_le(0)  # Time = 0 allows speed/acc parameters to govern trajectory
        speed_bytes = u16_to_le(speed_val)

        if use_acc:
            chunk = [acc_val & 0xFF, pos_bytes[0], pos_bytes[1], time_bytes[0], time_bytes[1], speed_bytes[0], speed_bytes[1]]
        else:
            chunk = [pos_bytes[0], pos_bytes[1], time_bytes[0], time_bytes[1], speed_bytes[0], speed_bytes[1]]

        servo_chunks[sid] = chunk

    start_addr = REG_ACC if use_acc else REG_GOAL_POSITION
    data_len = 7 if use_acc else 6
    return build_sync_write_packet(start_addr, data_len, servo_chunks)


# =============================================================================
# Response Decoding & Parsing
# =============================================================================

def decode_error_status(error_byte: int) -> Dict[str, bool]:
    """
    Decode STS3215 error bitmask (Register 0x41 or response status byte) into a dictionary of boolean flags.
    """
    return {
        "voltage_error": bool(error_byte & ERR_VOLTAGE),
        "sensor_error": bool(error_byte & ERR_SENSOR),
        "temperature_error": bool(error_byte & ERR_TEMPERATURE),
        "current_error": bool(error_byte & ERR_CURRENT),
        "angle_limit_error": bool(error_byte & ERR_ANGLE_LIMIT),
        "overload_error": bool(error_byte & ERR_OVERLOAD),
        "instruction_error": bool(error_byte & ERR_INSTRUCTION),
    }


@dataclass(frozen=True)
class ParsedResponse:
    """Structured representation of an STS3215 response packet."""
    servo_id: int
    length: int
    error_byte: int
    data: bytes
    checksum: int
    error_flags: Dict[str, bool]
    is_valid: bool


def parse_response_packet(packet: bytes) -> Optional[ParsedResponse]:
    """
    Parse a complete raw STS3215 response packet.
    Format: [0xFF, 0xFF, ID, Length, ErrorStatus, Data..., Checksum]
    Total packet length must equal Length + 4.
    Scans through multiple preambles if noise or 0xFF bytes precede the valid frame.
    """
    if len(packet) < 6:
        return None

    search_idx = 0
    candidate: Optional[ParsedResponse] = None

    while search_idx <= len(packet) - 6:
        try:
            idx = packet.index(PREAMBLE, search_idx)
        except ValueError:
            break

        frame = packet[idx:]
        if len(frame) < 6:
            break

        servo_id = frame[2]
        # In STS3215, response ID is 0..253 (0xFF is not a valid responding servo ID)
        if servo_id == 0xFF:
            search_idx = idx + 1
            continue

        length = frame[3]
        total_len = length + 4

        if len(frame) < total_len:
            search_idx = idx + 1
            continue

        target_frame = frame[:total_len]
        body = target_frame[2:-1]
        expected_chk = compute_checksum(body)
        received_chk = target_frame[-1]

        is_valid = (expected_chk == received_chk)
        error_byte = target_frame[4]
        data = bytes(target_frame[5:-1])
        error_flags = decode_error_status(error_byte)

        res = ParsedResponse(
            servo_id=servo_id,
            length=length,
            error_byte=error_byte,
            data=data,
            checksum=received_chk,
            error_flags=error_flags,
            is_valid=is_valid
        )

        if is_valid:
            return res
        elif candidate is None:
            candidate = res

        search_idx = idx + 1

    return candidate
