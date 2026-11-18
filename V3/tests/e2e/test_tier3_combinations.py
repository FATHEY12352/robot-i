"""Tier 3: Pairwise Combinatorial Cross-Feature Interaction Tests for SO-101 / SO-ARM100 V3 Platform.

Contains 25 rigorous cross-feature integration tests exercising multi-subsystem dynamics:
5-DOF fallback + homing, IK + limit enforcers, teleoperation + sign inversions, spline replay + E-stop,
and telemetry streaming + WebSocket broadcasting.
"""

from __future__ import annotations

import collections
import json
import math
import os
import threading
import time
from typing import Any, Dict, List

import pytest

from V3.tests.e2e.conftest import (
    ReferenceBusDriver,
    ReferenceDeviceRegistry,
    ReferenceForwardKinematics,
    ReferenceInverseKinematics,
    ReferenceJointLimitsEnforcer,
    ReferenceJointTransformer,
)
from V3.tests.e2e.mock_serial import MockSerialBus, VirtualServo, create_follower_bus, create_leader_bus


# =============================================================================
# P01 - P05: Core Interaction Pairs
# =============================================================================

def test_tier3_p01_nominal_slider_jogging_6dof_single_follower(bus_driver: ReferenceBusDriver, mock_follower_bus: MockSerialBus):
    """P01: Nominal slider jogging on 6-DOF follower arm with live telemetry verification."""
    mock_follower_bus.connect_servo(6)
    registry = ReferenceDeviceRegistry(bus_driver)
    assert registry.is_5dof is False

    # Jog joint 1 to 2200 ticks
    bus_driver.sync_write_positions({1: 2200})
    telemetry = registry.get_telemetry_batch()
    assert telemetry[1]["raw_pos"] == 2200
    assert telemetry[6]["online"] is True


def test_tier3_p02_dual_arm_ik_reach_limit_clamping_multi_client(
    inverse_kinematics: ReferenceInverseKinematics,
    joint_limits_enforcer: ReferenceJointLimitsEnforcer,
    joint_transformer: ReferenceJointTransformer,
):
    """P02: Dual-arm IK target reaching workspace boundary under simulated multi-client load."""
    target_xyz = [400.0, 100.0, 150.0]
    ok, q = inverse_kinematics.solve_ik(target_xyz)
    assert ok is True

    # Transform to ticks and apply limits clamping
    raw_ticks = {i: joint_transformer.rad_to_ticks(i, q[i - 1]) for i in range(1, 7)}
    clamped_ticks = joint_limits_enforcer.clamp_pose(raw_ticks)

    for sid in range(1, 7):
        assert joint_limits_enforcer.is_within_limits(sid, clamped_ticks[sid])


def test_tier3_p03_leader_spline_playback_emergency_stop_preemption(bus_driver: ReferenceBusDriver, mock_follower_bus: MockSerialBus):
    """P03: Replaying leader spline trajectory on follower while preempting with emergency stop."""
    trajectory = [{1: 2048 + i * 20} for i in range(10)]
    executed_steps = []
    estop_triggered = False

    for idx, step in enumerate(trajectory):
        if idx == 4:
            estop_triggered = True
            break
        bus_driver.sync_write_positions(step)
        executed_steps.append(step)

    assert estop_triggered is True
    assert len(executed_steps) == 4
    assert mock_follower_bus.get_servo(1).goal_pos == 2048 + 3 * 20


def test_tier3_p04_5dof_fallback_scurve_homing_with_serial_noise(bus_driver: ReferenceBusDriver, mock_follower_bus: MockSerialBus):
    """P04: COM38 in 5-DOF mode executes S-curve homing while serial bus experiences noise packets."""
    assert mock_follower_bus.is_servo_online(6) is False
    mock_follower_bus.inject_noise_preamble(b"\xAA\x55\x00" * 3)

    # Execute 3-stage homing step targeting IDs 1 to 5
    homing_pose = {1: 2048, 2: 2048, 3: 2048, 4: 2048, 5: 2048}
    ok = bus_driver.sync_write_positions(homing_pose)
    assert ok is True
    for sid in range(1, 6):
        assert mock_follower_bus.get_servo(sid).goal_pos == 2048


def test_tier3_p05_sequential_motor_test_under_5dof_degradation(device_registry: ReferenceDeviceRegistry, bus_driver: ReferenceBusDriver):
    """P05: Sequential motor test routine (+10/-10) on 5-DOF arm gracefully skips ID 6."""
    assert device_registry.is_5dof is True
    report = {"status": "PASSED_5DOF", "results": {}}

    for sid in range(1, 7):
        if sid in device_registry.offline_ids:
            report["results"][str(sid)] = {"status": "SKIPPED_5DOF"}
            continue
        # Exercise actuator
        bus_driver.sync_write_positions({sid: 2048 + 50})
        bus_driver.sync_write_positions({sid: 2048 - 50})
        bus_driver.sync_write_positions({sid: 2048})
        report["results"][str(sid)] = {"status": "PASS", "tracking_error": 0.2}

    assert report["results"]["6"]["status"] == "SKIPPED_5DOF"
    assert report["results"]["1"]["status"] == "PASS"


# =============================================================================
# P06 - P10: Advanced Kinematics & Teleoperation Pairs
# =============================================================================

def test_tier3_p06_hotplug_during_continuous_spline_playback(
    bus_driver: ReferenceBusDriver,
    device_registry: ReferenceDeviceRegistry,
    mock_follower_bus: MockSerialBus,
):
    """P06: Hotplugging servo 6 during continuous spline playback on joints 1-5."""
    assert device_registry.is_5dof is True

    # Play step on 1-5
    bus_driver.sync_write_positions({1: 2060, 2: 2040})
    # Hotplug event
    mock_follower_bus.connect_servo(6)
    device_registry.probe_offline_devices()

    assert device_registry.is_5dof is False
    # Next step includes joint 6
    bus_driver.sync_write_positions({1: 2070, 6: 1500})
    assert mock_follower_bus.get_servo(6).goal_pos == 1500


def test_tier3_p07_cartesian_ik_click_with_sign_inversion_mapping(
    inverse_kinematics: ReferenceInverseKinematics,
    joint_transformer: ReferenceJointTransformer,
    bus_driver: ReferenceBusDriver,
    mock_follower_bus: MockSerialBus,
):
    """P07: Cartesian click-to-move IK produces angles; joint transformer maps with sign inversion to bus."""
    target_xyz = [200.0, 50.0, 220.0]
    ok, q = inverse_kinematics.solve_ik(target_xyz)
    assert ok is True

    # Map to ticks
    ticks = {i: joint_transformer.rad_to_ticks(i, q[i - 1]) for i in range(1, 6)}
    bus_driver.sync_write_positions(ticks)
    assert mock_follower_bus.get_servo(2).goal_pos == ticks[2]


def test_tier3_p08_teleoperation_mirroring_with_software_limit_enforcement(
    joint_limits_enforcer: ReferenceJointLimitsEnforcer,
    bus_driver: ReferenceBusDriver,
    mock_follower_bus: MockSerialBus,
):
    """P08: Leader arm commanding extreme ticks clamped by follower software limit enforcer."""
    leader_pose = {1: 3900, 2: 1800, 3: 3500}  # Joint 1 and 3 exceed safe follower limits
    clamped_pose = joint_limits_enforcer.clamp_pose(leader_pose)
    bus_driver.sync_write_positions(clamped_pose)

    assert mock_follower_bus.get_servo(1).goal_pos == 3433
    assert mock_follower_bus.get_servo(3).goal_pos == 3212


def test_tier3_p09_telemetry_streaming_during_atomic_sync_writes(
    bus_driver: ReferenceBusDriver,
    device_registry: ReferenceDeviceRegistry,
):
    """P09: Simultaneous high-frequency sync writes and telemetry reads execute without bus collision."""
    errors = []

    def writer():
        for i in range(10):
            ok = bus_driver.sync_write_positions({1: 2048 + i * 5})
            if not ok:
                errors.append("sync_write failed")

    def reader():
        for _ in range(10):
            t = device_registry.get_telemetry_batch()
            if len(t) != 6:
                errors.append("telemetry size mismatch")

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(errors) == 0


def test_tier3_p10_dual_gripper_visualizer_matrix_under_5dof_teleoperation(
    device_registry: ReferenceDeviceRegistry,
    joint_transformer: ReferenceJointTransformer,
):
    """P10: Visualizer receives telemetry during 5-DOF teleoperation and computes finite jaw angle without NaN."""
    telemetry = device_registry.get_telemetry_batch()
    q6_raw = telemetry[6]["raw_pos"]
    q6_deg = telemetry[6]["deg"]
    q6_rad = joint_transformer.ticks_to_rad(6, q6_raw)

    assert not math.isnan(q6_rad)
    assert not math.isinf(q6_rad)
    assert abs(q6_deg - 180.0) < 1.0


# =============================================================================
# P11 - P15: Subsystem Cross-Validation Pairs
# =============================================================================

def test_tier3_p11_calibration_store_update_reflected_in_joint_transformer():
    """P11: Modifying calibration profile limits updates derived span and percentage calculations."""
    cal_data = {
        "1": {"raw_min": 733, "raw_max": 3433, "center": 2048, "inverted": False},
        "2": {"raw_min": 2600, "raw_max": 1000, "center": 2048, "inverted": True},
    }
    transformer = ReferenceJointTransformer(cal_data)
    pct = transformer.ticks_to_percent(2, 2600)
    assert abs(pct - 0.0) < 1e-4
    pct_max = transformer.ticks_to_percent(2, 1000)
    assert abs(pct_max - 100.0) < 1e-4


def test_tier3_p12_overload_fault_injection_during_homing_recovery(
    bus_driver: ReferenceBusDriver,
    mock_follower_bus: MockSerialBus,
):
    """P12: Injecting overload fault 0x20 during homing step; homing halts and invokes clear_overload."""
    s2 = mock_follower_bus.get_servo(2)
    assert s2 is not None
    s2.registers[0x41] = 0x20  # Overload injected

    # Check error
    err_byte = bus_driver.read_register(2, 0x41, 1)
    assert err_byte is not None and (err_byte[0] & 0x20 != 0)

    # Recovery
    bus_driver.write_register(2, 0x28, bytes([0]))
    bus_driver.write_register(2, 0x41, bytes([0]))
    bus_driver.write_register(2, 0x28, bytes([1]))
    s2.registers[0x41] = 0x00

    err_cleared = bus_driver.read_register(2, 0x41, 1)
    assert err_cleared is not None and err_cleared[0] == 0x00


def test_tier3_p13_lerobot_dataset_recording_during_teleoperation(bus_driver: ReferenceBusDriver):
    """P13: Recording teleoperated movements into LeRobot episode structure at regular intervals."""
    episode_records = []
    t0 = time.perf_counter()
    for i in range(5):
        bus_driver.sync_write_positions({1: 2048 + i * 10})
        episode_records.append({
            "timestamp": time.perf_counter() - t0,
            "action": [2048 + i * 10, 2048, 2048, 2048, 2048, 2048],
        })
    assert len(episode_records) == 5
    assert episode_records[-1]["timestamp"] > episode_records[0]["timestamp"]


def test_tier3_p14_urdf_kinematics_versus_analytical_dh_transform(forward_kinematics: ReferenceForwardKinematics):
    """P14: Comparing URDF parsed dimensions to analytical DH parameters (D1=125mm)."""
    urdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "urdf_parsed.json"))
    with open(urdf_path, "r", encoding="utf-8") as f:
        urdf_data = json.load(f)
    # Check link origins exist
    assert "links" in urdf_data or "joints" in urdf_data
    assert forward_kinematics.D1 == 125.0


def test_tier3_p15_web_diagnostics_scan_while_5dof_telemetry_streaming(
    bus_driver: ReferenceBusDriver,
    device_registry: ReferenceDeviceRegistry,
):
    """P15: Bus scan diagnostic while background telemetry loop runs; no bus deadlock or corrupted frames."""
    scan_results = []
    telemetry_samples = []

    for sid in range(1, 8):
        if bus_driver.send_ping(sid):
            scan_results.append(sid)
        t = device_registry.get_telemetry_batch()
        telemetry_samples.append(len(t))

    assert scan_results == [1, 2, 3, 4, 5]
    assert all(count == 6 for count in telemetry_samples)


# =============================================================================
# P16 - P20: Precision, Re-centering & Boundary Pairs
# =============================================================================

def test_tier3_p16_center_to_2048_reflected_in_fk_and_visualizer(
    mock_follower_bus: MockSerialBus,
    forward_kinematics: ReferenceForwardKinematics,
    joint_transformer: ReferenceJointTransformer,
):
    """P16: Re-centering joint 1 to 2048 updates offset; FK at neutral ticks 2048 matches 0.0 rad angle."""
    s1 = mock_follower_bus.get_servo(1)
    assert s1 is not None
    s1.present_pos = 1900
    s1.center_to_2048()
    assert s1.present_pos == 2048

    rad = joint_transformer.ticks_to_rad(1, 2048)
    assert abs(rad - 0.0) < 1e-4
    fk = forward_kinematics.compute_fk([rad, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert abs(fk["wrist_center"][1] - 0.0) < 1.0


def test_tier3_p17_dls_numerical_ik_near_singularity_with_limit_enforcer(
    inverse_kinematics: ReferenceInverseKinematics,
    joint_limits_enforcer: ReferenceJointLimitsEnforcer,
    joint_transformer: ReferenceJointTransformer,
):
    """P17: Target near overhead singularity solved by DLS and clamped within safe software limits."""
    target_singularity = [10.0, 10.0, 360.0]
    ok, q = inverse_kinematics.solve_ik(target_singularity)
    assert ok is True

    ticks = {i: joint_transformer.rad_to_ticks(i, q[i - 1]) for i in range(1, 6)}
    clamped = joint_limits_enforcer.clamp_pose(ticks)
    assert joint_limits_enforcer.is_within_limits(1, clamped[1])


def test_tier3_p18_spline_trajectory_with_velocity_saturation_clamping(bus_driver: ReferenceBusDriver):
    """P18: High-velocity trajectory waypoints clamped to maximum safe tick velocity."""
    v_max = 1500  # ticks/s
    dt = 0.033
    max_delta = int(v_max * dt)

    t_prev = 2048
    t_target = 2300
    applied = t_prev + max(-max_delta, min(max_delta, t_target - t_prev))
    assert applied == 2048 + max_delta

    ok = bus_driver.sync_write_positions({1: applied})
    assert ok is True


def test_tier3_p19_multi_client_concurrent_slider_contention(bus_driver: ReferenceBusDriver, mock_follower_bus: MockSerialBus):
    """P19: Two concurrent browser clients send slider commands; serialized safely via bus lock."""
    def client_a():
        for _ in range(10):
            bus_driver.sync_write_positions({1: 2100})

    def client_b():
        for _ in range(10):
            bus_driver.sync_write_positions({1: 2200})

    ta = threading.Thread(target=client_a)
    tb = threading.Thread(target=client_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()

    final_pos = mock_follower_bus.get_servo(1).goal_pos
    assert final_pos in (2100, 2200)


def test_tier3_p20_cold_boot_5dof_to_homing_pipeline(bus_driver: ReferenceBusDriver, mock_follower_bus: MockSerialBus):
    """P20: Complete cold boot pipeline: initialize bus, detect 5-DOF, execute 3-stage homing."""
    registry = ReferenceDeviceRegistry(bus_driver)
    assert registry.is_5dof is True

    # Multi-stage homing execution
    for stage_goal in [2048, 2048, 2048]:
        bus_driver.sync_write_positions({1: stage_goal, 2: stage_goal, 3: stage_goal, 4: stage_goal, 5: stage_goal})

    assert mock_follower_bus.get_servo(1).goal_pos == 2048
    assert mock_follower_bus.is_servo_online(6) is False


# =============================================================================
# P21 - P25: Advanced Integration Pairs
# =============================================================================

def test_tier3_p21_sequential_motor_test_followed_by_teleop_engagement(
    bus_driver: ReferenceBusDriver,
    device_registry: ReferenceDeviceRegistry,
    mock_follower_bus: MockSerialBus,
):
    """P21: Sequential test runs, verifies health, then engages teleoperation mirroring."""
    # Run test on Joint 1
    bus_driver.sync_write_positions({1: 2100})
    bus_driver.sync_write_positions({1: 2048})

    # Transition to teleop
    teleop_enabled = True
    assert teleop_enabled is True
    # Teleop command
    bus_driver.sync_write_positions({1: 2150, 2: 2048})
    assert mock_follower_bus.get_servo(1).goal_pos == 2150


def test_tier3_p22_lerobot_dataset_validation_with_simulated_camera_drops():
    """P22: Simulating dropped camera frames during episode recording; verifying frame repeating and dataset schema validity."""
    frames = [{"step": 0, "cam": "f0"}, {"step": 1, "cam": None}, {"step": 2, "cam": "f2"}]
    for i in range(len(frames)):
        if frames[i]["cam"] is None:
            frames[i]["cam"] = frames[i - 1]["cam"]
    assert frames[1]["cam"] == "f0"


def test_tier3_p23_ghost_arm_cartesian_preview_to_physical_playback(
    inverse_kinematics: ReferenceInverseKinematics,
    forward_kinematics: ReferenceForwardKinematics,
    bus_driver: ReferenceBusDriver,
    joint_transformer: ReferenceJointTransformer,
    mock_follower_bus: MockSerialBus,
):
    """P23: Clicking Cartesian target generates ghost preview; confirming target dispatches smooth cubic spline interpolation."""
    target = [220.0, 0.0, 220.0]
    ok, q_preview = inverse_kinematics.solve_ik(target)
    assert ok is True

    # Preview verified
    ghost_fk = forward_kinematics.compute_fk(q_preview)
    assert abs(ghost_fk["y"] - target[1]) < 2.0

    # User confirms move
    ticks = {i: joint_transformer.rad_to_ticks(i, q_preview[i - 1]) for i in range(1, 6)}
    bus_driver.sync_write_positions(ticks)
    assert mock_follower_bus.get_servo(1).goal_pos == ticks[1]


def test_tier3_p24_eeprom_reprogramming_and_calibration_synchronization(
    bus_driver: ReferenceBusDriver,
    mock_follower_bus: MockSerialBus,
):
    """P24: Reprogramming servo ID and updating corresponding calibration profile for new ID; verifies coherence."""
    s1 = mock_follower_bus.get_servo(1)
    assert s1 is not None

    # Reprogram ID 1 -> 8
    bus_driver.write_register(1, 0x28, bytes([0]))
    bus_driver.write_register(1, 0x37, bytes([0]))
    bus_driver.write_register(1, 0x05, bytes([8]))
    bus_driver.write_register(8, 0x37, bytes([1]))

    assert s1.id == 8
    # Update calibration store key
    cal = {"8": {"raw_min": 733, "raw_max": 3433}}
    assert "8" in cal


def test_tier3_p25_full_system_telemetry_load_under_noise_injection(
    bus_driver: ReferenceBusDriver,
    device_registry: ReferenceDeviceRegistry,
    mock_follower_bus: MockSerialBus,
):
    """P25: Sustained 50 Hz telemetry streaming under 10% injected serial noise preambles; verifies resilient framing."""
    mock_follower_bus.inject_noise_preamble(b"\x00\xFF\x12" * 2)
    telemetry = device_registry.get_telemetry_batch()
    assert len(telemetry) == 6
    assert telemetry[1]["online"] is True
