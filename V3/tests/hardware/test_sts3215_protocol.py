"""
Comprehensive Unit Tests for STS3215 Protocol Specification & Codec.
"""

import struct
import pytest
from V3.hardware.sts3215_protocol import (
    BROADCAST_ID,
    ERR_ANGLE_LIMIT,
    ERR_CURRENT,
    ERR_INSTRUCTION,
    ERR_OVERLOAD,
    ERR_SENSOR,
    ERR_TEMPERATURE,
    ERR_VOLTAGE,
    INST_ACTION,
    INST_PING,
    INST_READ,
    INST_REG_WRITE,
    INST_RESET,
    INST_SYNC_WRITE,
    INST_WRITE,
    PREAMBLE,
    REG_ACC,
    REG_BAUD,
    REG_ERROR_STATUS,
    REG_GOAL_POSITION,
    REG_GOAL_SPEED,
    REG_ID,
    REG_LOCK,
    REG_MAX_ANGLE_LIMIT,
    REG_MIN_ANGLE_LIMIT,
    REG_MOVE_STATUS,
    REG_OFFSET,
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
    build_sync_write_packet,
    build_sync_write_positions_packet,
    build_write_packet,
    compute_checksum,
    decode_error_status,
    le_to_s16,
    le_to_u16,
    parse_response_packet,
    s16_to_le,
    u16_to_le,
    validate_checksum,
)


def test_checksum_calculation_verbatim():
    """Verify checksum on authoritative sample packets from Feetech SDK."""
    # 1. PING ID 1: [ID=1, Len=2, Inst=1] -> sum=4 -> (~4)&0xFF = 0xFB = 251
    body_ping = [0x01, 0x02, 0x01]
    assert compute_checksum(body_ping) == 0xFB

    # 2. READ ID 2 reg 0x38 len 15: [2, 4, 2, 56, 15] -> sum=79 -> (~79)&0xFF = 176 = 0xB0
    body_read = [0x02, 0x04, 0x02, 0x38, 0x0F]
    assert compute_checksum(body_read) == 0xB0

    # 3. SYNC WRITE 2 servos to 2048, speed 500: body from Monograph Appendix
    body_sync = [0xFE, 18, 0x83, 0x2A, 6, 1, 0, 8, 0, 0, 244, 1, 2, 0, 8, 0, 0, 244, 1]
    assert compute_checksum(body_sync) == 0x3F


def test_checksum_rollover_masking():
    """Verify sum > 255 correctly wraps within 0..255 range."""
    large_body = [200, 200, 116]  # sum = 516 = 2*256 + 4
    expected = (~4) & 0xFF
    assert compute_checksum(large_body) == expected
    assert 0 <= compute_checksum(large_body) <= 255


def test_validate_checksum():
    """Verify validate_checksum helper on valid and corrupted bodies."""
    valid_stream = [0x01, 0x02, 0x01, 0xFB]
    assert validate_checksum(valid_stream) is True

    corrupted_stream = [0x01, 0x02, 0x01, 0xFA]
    assert validate_checksum(corrupted_stream) is False

    too_short = [0x01]
    assert validate_checksum(too_short) is False


def test_little_endian_word_conversions():
    """Verify 16-bit unsigned and signed conversions to and from Little-Endian."""
    test_values_u16 = [0, 1, 500, 2048, 4095, 65535]
    for val in test_values_u16:
        packed = u16_to_le(val)
        assert len(packed) == 2
        assert packed[0] == (val & 0xFF)
        assert packed[1] == ((val >> 8) & 0xFF)
        unpacked = le_to_u16(packed)
        assert unpacked == val

    test_values_s16 = [-32768, -1000, -1, 0, 1, 1500, 32767]
    for val in test_values_s16:
        packed = s16_to_le(val)
        assert len(packed) == 2
        unpacked = le_to_s16(packed)
        assert unpacked == val


def test_build_ping_packet():
    """Verify PING packet generation."""
    pkt1 = build_ping_packet(1)
    assert pkt1 == bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB])

    pkt6 = build_ping_packet(6)
    chk6 = (~(6 + 2 + 1)) & 0xFF
    assert pkt6 == bytes([0xFF, 0xFF, 0x06, 0x02, 0x01, chk6])


def test_build_read_packet():
    """Verify READ packet generation."""
    pkt = build_read_packet(3, 0x38, 15)
    expected_body = [0x03, 0x04, 0x02, 0x38, 0x0F]
    expected_chk = compute_checksum(expected_body)
    assert pkt == bytes([0xFF, 0xFF] + expected_body + [expected_chk])


def test_build_write_packet():
    """Verify WRITE packet generation."""
    # Write torque enable = 1 on servo 4
    pkt = build_write_packet(4, REG_TORQUE_ENABLE, bytes([1]))
    expected_body = [0x04, 0x04, 0x03, 0x28, 0x01]
    expected_chk = compute_checksum(expected_body)
    assert pkt == bytes([0xFF, 0xFF] + expected_body + [expected_chk])


def test_build_reg_write_and_action():
    """Verify REG_WRITE and ACTION packet generation."""
    rw_pkt = build_reg_write_packet(2, REG_GOAL_POSITION, bytes([0x00, 0x08]))
    assert rw_pkt[4] == INST_REG_WRITE

    act_pkt = build_action_packet()
    assert act_pkt[2] == BROADCAST_ID
    assert act_pkt[4] == INST_ACTION


def test_build_reset_packet():
    """Verify RESET packet generation."""
    rst_pkt = build_reset_packet(5)
    assert rst_pkt[2] == 5
    assert rst_pkt[4] == INST_RESET
    assert validate_checksum(rst_pkt[2:]) is True


def test_build_sync_write_positions_packet():
    """Verify atomic SYNC_WRITE packet generation for multiple servos."""
    targets = {1: 2048, 2: 1500, 3: 2500}
    speeds = {1: 300, 2: 400, 3: 500}
    accs = {1: 10, 2: 20, 3: 30}

    pkt = build_sync_write_positions_packet(targets, speeds=speeds, accs=accs, use_acc=True)
    assert pkt[:2] == PREAMBLE
    assert pkt[2] == BROADCAST_ID
    assert pkt[4] == INST_SYNC_WRITE
    assert pkt[5] == REG_ACC  # Start address
    assert pkt[6] == 7        # 7 bytes per servo: [ACC, Pos_L, Pos_H, Time_L, Time_H, Spd_L, Spd_H]
    assert validate_checksum(pkt[2:]) is True

    # Check payload chunk for servo 1
    # sid=1 at offset 7
    assert pkt[7] == 1
    assert pkt[8] == 10  # acc
    assert le_to_u16(pkt[9:11]) == 2048
    assert le_to_u16(pkt[13:15]) == 300


def test_parse_response_packet_valid():
    """Verify parser extracts payload from valid STS3215 response frame."""
    # Servo 1 response: Pos=2048, Spd=0, Load=0, Volt=12.2V (122), Temp=35, Err=0, Curr=150mA
    tel_payload = bytes([0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 122, 35, 0, 0, 0, 0, 0, 150, 0])
    err_byte = 0x00
    body = [1, len(tel_payload) + 2, err_byte] + list(tel_payload)
    chk = compute_checksum(body)
    raw_frame = PREAMBLE + bytes(body) + bytes([chk])

    parsed = parse_response_packet(raw_frame)
    assert parsed is not None
    assert parsed.is_valid is True
    assert parsed.servo_id == 1
    assert parsed.error_byte == 0
    assert parsed.data == tel_payload
    assert parsed.checksum == chk
    assert parsed.error_flags["overload_error"] is False


def test_parse_response_packet_with_leading_noise():
    """Verify parser synchronizes to 0xFF 0xFF even with leading garbage bytes."""
    valid_body = [3, 2, 0]  # PING response from servo 3, status 0
    valid_chk = compute_checksum(valid_body)
    packet = bytes([0xAA, 0x55, 0x00, 0xFF]) + PREAMBLE + bytes(valid_body) + bytes([valid_chk])

    parsed = parse_response_packet(packet)
    assert parsed is not None
    assert parsed.is_valid is True
    assert parsed.servo_id == 3


def test_parse_response_packet_corrupt_checksum():
    """Verify parser flags invalid checksum."""
    body = [1, 2, 0]
    bad_chk = 0x00  # wrong checksum
    packet = PREAMBLE + bytes(body) + bytes([bad_chk])

    parsed = parse_response_packet(packet)
    assert parsed is not None
    assert parsed.is_valid is False


def test_decode_error_status_bitfield():
    """Verify bitfield decoding of Register 0x41 error flags."""
    # Zero error
    flags_clean = decode_error_status(0x00)
    assert all(val is False for val in flags_clean.values())

    # Individual error bits
    assert decode_error_status(ERR_VOLTAGE)["voltage_error"] is True
    assert decode_error_status(ERR_SENSOR)["sensor_error"] is True
    assert decode_error_status(ERR_TEMPERATURE)["temperature_error"] is True
    assert decode_error_status(ERR_CURRENT)["current_error"] is True
    assert decode_error_status(ERR_ANGLE_LIMIT)["angle_limit_error"] is True
    assert decode_error_status(ERR_OVERLOAD)["overload_error"] is True
    assert decode_error_status(ERR_INSTRUCTION)["instruction_error"] is True

    # Composite error: Overload (0x20) + Temp (0x04) = 0x24
    flags_multi = decode_error_status(0x24)
    assert flags_multi["overload_error"] is True
    assert flags_multi["temperature_error"] is True
    assert flags_multi["voltage_error"] is False


def test_register_constants_coverage():
    """Verify required register constants are accurately defined."""
    assert REG_ID == 0x05
    assert REG_BAUD == 0x06
    assert REG_MIN_ANGLE_LIMIT == 0x09
    assert REG_MAX_ANGLE_LIMIT == 0x0B
    assert REG_OFFSET == 0x1F
    assert REG_TORQUE_ENABLE == 0x28
    assert REG_ACC == 0x29
    assert REG_GOAL_POSITION == 0x2A
    assert REG_GOAL_SPEED == 0x2E
    assert REG_LOCK == 0x37
    assert REG_PRESENT_POS == 0x38
    assert REG_PRESENT_SPEED == 0x3A
    assert REG_PRESENT_LOAD == 0x3C
    assert REG_PRESENT_VOLT == 0x3E
    assert REG_PRESENT_TEMP == 0x3F
    assert REG_ERROR_STATUS == 0x41
    assert REG_MOVE_STATUS == 0x42
    assert REG_PRESENT_CURRENT == 0x45
