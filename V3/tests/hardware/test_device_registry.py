"""
Comprehensive Unit & Concurrency Tests for DeviceRegistry & 5-DOF Fallback.
"""

import math
import threading
import time
import pytest

from V3.hardware.bus_driver import BusDriver, MockSerialBus
from V3.hardware.device_registry import DeviceRegistry, ServoTelemetry, TelemetryBatch


def test_registry_initial_state_5dof():
    """Verify Follower arm initializes in 5-DOF mode with ID 6 offline."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6})

    assert registry.is_5dof is True
    assert registry.active_ids == {1, 2, 3, 4, 5}
    assert registry.offline_ids == {6}
    assert registry.expected_ids == {1, 2, 3, 4, 5, 6}


def test_telemetry_latency_5dof_guarantee():
    """Verify 5-DOF telemetry query avoids the 80ms dead bus penalty."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6})

    t0 = time.perf_counter()
    batch = registry.get_telemetry_batch()
    dt = time.perf_counter() - t0

    # In mock execution, latency is typically < 0.005s; must never suffer 80ms timeout
    assert dt < 0.02, f"Telemetry loop took {dt:.4f}s, expected < 0.02s"

    # All 6 servos must be present in the returned batch
    assert len(batch) == 6
    for sid in range(1, 6):
        assert batch[sid].is_online is True
        assert batch[sid].position == 2048

    # Unwired servo 6 has safe finite defaults without NaN
    s6 = batch[6]
    assert s6.is_online is False
    assert s6.position == 2048
    assert not math.isnan(s6.angle_deg)
    assert not math.isnan(s6.voltage)
    assert not math.isnan(s6.load)


def test_hotplug_promotion_and_callback():
    """Verify connecting servo 6 triggers hotplug promotion and turns off 5-DOF."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6})

    connected_events = []
    registry.on_device_connected(lambda sid: connected_events.append(sid))

    # Connect servo 6
    mock_bus.connect_servo(6, initial_pos=2048)
    registry.probe_offline_devices()

    assert 6 in connected_events
    assert 6 in registry.active_ids
    assert 6 not in registry.offline_ids
    assert registry.is_5dof is False


def test_hotunplug_failover_demotion_and_callback():
    """Verify disconnecting an active servo demotes it to offline after consecutive failures."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5, 6})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6}, failure_threshold=3)

    disconnected_events = []
    registry.on_device_disconnected(lambda sid: disconnected_events.append(sid))

    # Unplug servo 3
    mock_bus.disconnect_servo(3)

    # Poll 3 times to exceed failure threshold
    for _ in range(3):
        registry.get_telemetry_batch()

    assert 3 in disconnected_events
    assert 3 in registry.offline_ids
    assert 3 not in registry.active_ids


def test_background_prober_thread():
    """Verify background prober daemon automatically detects connected servos at runtime."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    # Fast 0.05s probe interval for testing
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6}, probe_interval=0.05)

    assert 6 in registry.offline_ids
    registry.start_background_prober()

    try:
        # Plug in servo 6
        mock_bus.connect_servo(6)

        # Wait up to 0.3s for background prober to cycle
        deadline = time.time() + 0.3
        while time.time() < deadline:
            if 6 in registry.active_ids:
                break
            time.sleep(0.01)

        assert 6 in registry.active_ids
        assert 6 not in registry.offline_ids
    finally:
        registry.stop_background_prober()


def test_concurrency_stress_telemetry_and_probing():
    """Verify high-frequency telemetry and background probing never raise Set changed size or deadlock."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6}, probe_interval=0.01)

    stop_flag = threading.Event()
    exceptions = []

    def fast_telemetry_worker():
        while not stop_flag.is_set():
            try:
                batch = registry.get_telemetry_batch()
                assert len(batch) == 6
            except Exception as e:
                exceptions.append(e)
            time.sleep(0.001)

    def prober_flipper_worker():
        for i in range(20):
            if stop_flag.is_set():
                break
            if i % 2 == 0:
                mock_bus.connect_servo(6)
            else:
                mock_bus.disconnect_servo(6)
            registry.probe_offline_devices()
            time.sleep(0.005)

    t1 = threading.Thread(target=fast_telemetry_worker)
    t2 = threading.Thread(target=prober_flipper_worker)

    t1.start()
    t2.start()

    t2.join(timeout=2.0)
    stop_flag.set()
    t1.join(timeout=1.0)

    assert len(exceptions) == 0, f"Encountered concurrency exceptions: {exceptions}"


def test_telemetry_batch_schema_and_dict_access():
    """Verify ServoTelemetry and TelemetryBatch conform to WebSocket schema and dict access."""
    mock_bus = MockSerialBus(port="COM38", active_ids={1, 2, 3, 4, 5})
    driver = BusDriver(port="COM38", custom_serial=mock_bus)
    registry = DeviceRegistry(driver=driver, expected_ids={1, 2, 3, 4, 5, 6})

    batch_map = registry.get_telemetry_batch()
    s1 = batch_map[1]

    # Subscripting by key
    assert s1["id"] == 1
    assert s1["raw_pos"] == 2048
    assert s1["deg"] == 180.0
    assert s1["speed"] == 0
    assert s1["volt"] == 12.2
    assert s1["temp"] == 34
    assert s1["err"] == 0
    assert s1["online"] is True

    # Dict conversion
    s1_dict = s1.to_dict()
    assert s1_dict["pos"] == 2048
    assert s1_dict["deg"] == 180.0

    # Batch container
    batch_obj = registry.get_batch()
    assert batch_obj.is_5dof is True
    assert batch_obj.arm_name == "follower"
    assert len(batch_obj) == 6
    assert 1 in batch_obj
    assert batch_obj[1]["volt"] == 12.2

    ws_msg = batch_obj.to_ws_message()
    assert ws_msg["type"] == "telemetry"
    assert ws_msg["dof"] == 5
    assert "1" in ws_msg["servos"]
    assert "6" in ws_msg["servos"]
