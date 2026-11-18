"""
Comprehensive Unit & Mock Tests for Serial Bus Driver & MockSerialBus.
"""

import threading
import time
import pytest

from V3.hardware.bus_driver import (
    BusChecksumError,
    BusDriver,
    BusDriverError,
    BusTimeoutError,
    MockSerialBus,
    SimulatedSTS3215,
)
from V3.hardware.sts3215_protocol import (
    REG_GOAL_POSITION,
    REG_PRESENT_POS,
    REG_TORQUE_ENABLE,
    le_to_u16,
    u16_to_le,
)


def test_mock_serial_lifecycle():
    """Verify basic open, close, buffer management on MockSerialBus."""
    bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    assert bus.is_open is True
    assert bus.port == "COM38"
    assert bus.in_waiting == 0

    bus.close()
    assert bus.is_open is False
    bus.open()
    assert bus.is_open is True


def test_bus_driver_connect_disconnect():
    """Verify BusDriver open, close, and properties."""
    mock_bus = MockSerialBus(port="COM38")
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    assert driver.connect() is True
    assert driver.is_connected is True
    assert driver.is_open is True

    driver.disconnect()
    assert driver.is_connected is False


def test_send_ping_active_and_offline():
    """Verify PING succeeds on active servos and fails safely on offline ones."""
    # 5-DOF bus: Servos 1-5 active, Servo 6 offline
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5}, timeout=0.015)
    driver = BusDriver(port="COM38", custom_serial=mock_bus, timeout=0.015)

    assert driver.send_ping(1) is True
    assert driver.send_ping(2) is True
    assert driver.send_ping(5) is True

    # Offline servo 6
    assert driver.send_ping(6) is False
    # Non-existent servo 15
    assert driver.send_ping(15) is False


def test_read_register_present_position():
    """Verify reading 16-bit present position register."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3})
    servo2 = mock_bus.get_servo(2)
    assert servo2 is not None
    servo2.present_pos = 1850

    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    raw = driver.read_register(2, REG_PRESENT_POS, 2)
    assert raw is not None
    assert len(raw) == 2
    assert le_to_u16(raw) == 1850


def test_read_register_full_telemetry_block():
    """Verify reading 15 bytes starting at 0x38."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1})
    s1 = mock_bus.get_servo(1)
    assert s1 is not None
    s1.present_pos = 2048

    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    raw = driver.read_register(1, 0x38, 15)
    assert raw is not None
    assert len(raw) == 15
    assert le_to_u16(raw[0:2]) == 2048
    assert raw[6] == 122  # 12.2V default
    assert raw[7] == 34   # 34°C default


def test_write_register_torque_enable():
    """Verify writing torque enable updates simulated servo register."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2})
    s1 = mock_bus.get_servo(1)
    assert s1 is not None
    assert s1.registers[REG_TORQUE_ENABLE] == 0

    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    # Turn torque ON
    assert driver.write_register(1, REG_TORQUE_ENABLE, bytes([1])) is True
    assert s1.registers[REG_TORQUE_ENABLE] == 1

    # Turn torque OFF
    assert driver.write_register(1, REG_TORQUE_ENABLE, bytes([0])) is True
    assert s1.registers[REG_TORQUE_ENABLE] == 0


def test_sync_write_positions_broadcast():
    """Verify atomic broadcast sync_write_positions updates multiple servos."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    # Enable torque so present pos tracks goal pos
    for sid in (1, 2, 3):
        s = mock_bus.get_servo(sid)
        assert s is not None
        s.registers[REG_TORQUE_ENABLE] = 1

    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    targets = {1: 1500, 2: 2500, 3: 3000}
    assert driver.sync_write_positions(targets, speed=400, acc=10) is True

    s1 = mock_bus.get_servo(1)
    s2 = mock_bus.get_servo(2)
    s3 = mock_bus.get_servo(3)
    assert s1 is not None and s1.goal_pos == 1500
    assert s2 is not None and s2.goal_pos == 2500
    assert s3 is not None and s3.goal_pos == 3000

    # Because torque is enabled, present_pos tracks goal_pos
    assert s1.present_pos == 1500
    assert s2.present_pos == 2500
    assert s3.present_pos == 3000


def test_echo_cancellation_active():
    """Verify echo cancellation handles half-duplex USB-UART loopback."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1}, echo_enabled=True)
    driver = BusDriver(port="COM38", custom_serial=mock_bus, enable_echo_cancellation=True)

    # Ping should succeed despite echo
    assert driver.send_ping(1) is True

    # Read register should succeed despite echo
    raw = driver.read_register(1, REG_PRESENT_POS, 2)
    assert raw is not None
    assert len(raw) == 2


def test_checksum_corruption_handling():
    """Verify driver drops corrupted packets and recovers on next transaction."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)

    # Invalidate checksum on mock bus
    mock_bus.corrupt_checksum = True
    assert driver.read_register(1, REG_PRESENT_POS, 2) is None

    # Restore checksum
    mock_bus.corrupt_checksum = False
    assert driver.read_register(1, REG_PRESENT_POS, 2) is not None


def test_thread_safe_concurrent_arbitration():
    """Verify concurrent reads and writes from multiple threads do not cause deadlocks or corruptions."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)

    errors = []

    def reader_worker(sid: int):
        for _ in range(25):
            res = driver.read_register(sid, REG_PRESENT_POS, 2)
            if res is None:
                errors.append(f"Reader failed for servo {sid}")

    def writer_worker():
        for i in range(25):
            pos = 2000 + (i * 10)
            ok = driver.sync_write_positions({1: pos, 2: pos, 3: pos})
            if not ok:
                errors.append("Sync write failed")

    threads = [
        threading.Thread(target=reader_worker, args=(1,)),
        threading.Thread(target=reader_worker, args=(2,)),
        threading.Thread(target=reader_worker, args=(3,)),
        threading.Thread(target=writer_worker),
        threading.Thread(target=writer_worker),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Encountered concurrency errors: {errors}"
