"""
Unit tests for SO-101 Robotics Studio V4.
Covers requirements validation, logger, env manager, hardware wizard, process runner (Mandatory Fixes 1, 2, 3), and cloud packager.
"""

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest

# Ensure V4 root is on sys.path
V4_ROOT = Path(__file__).resolve().parents[1]
if str(V4_ROOT) not in sys.path:
    sys.path.insert(0, str(V4_ROOT))

from core.logger import StudioLogger, get_logger
from core.env_manager import EnvManager
from core.hardware_wizard import HardwareWizard
from core.process_runner import ProcessRunner
from core.cloud_packager import CloudPackager


# =============================================================================
# 1. Requirements Validation (Mandatory Fix 1)
# =============================================================================

def test_requirements_gui_valid():
    req_file = V4_ROOT / "requirements_gui.txt"
    assert req_file.exists(), "requirements_gui.txt must exist"
    content = req_file.read_text(encoding="utf-8")

    # Mandatory Fix 1: customtkinter>=5.2.0 (version 6.0.0 does not exist on PyPI)
    assert "customtkinter>=5.2.0" in content, "Must specify customtkinter>=5.2.0"
    assert "customtkinter==6.0.0" not in content, "Must not specify non-existent version 6.0.0"
    assert "customtkinter>=6.0.0" not in content, "Must not specify non-existent version 6.0.0"
    assert "pyserial" in content
    assert "opencv-python" in content
    assert "pillow" in content


# =============================================================================
# 2. Logger Tests
# =============================================================================

def test_studio_logger_lifecycle(tmp_path):
    log_file = tmp_path / "test_studio.log"
    logger = StudioLogger(log_file=log_file)

    received = []
    def log_listener(lvl_name, lvl_no, msg):
        received.append((lvl_name, msg))

    logger.subscribe(log_listener)

    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    # Give worker thread a moment to flush
    import time
    time.sleep(0.4)

    assert any("Test info message" in r[1] for r in received)
    assert any("Test warning message" in r[1] for r in received)
    assert any("Test error message" in r[1] for r in received)

    logger.unsubscribe(log_listener)
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test info message" in content


# =============================================================================
# 3. Environment Manager Tests
# =============================================================================

def test_env_manager_detection():
    mgr = EnvManager(root_dir=V4_ROOT)
    summary = mgr.get_env_summary()

    assert "os" in summary
    assert "python_version" in summary
    assert "gpu" in summary
    assert "lerobot" in summary

    gpu = summary["gpu"]
    assert "cuda_available" in gpu
    assert "device_name" in gpu
    assert "vram_gb" in gpu

    lerobot = summary["lerobot"]
    assert "installed" in lerobot
    assert "cli_record" in lerobot
    assert "cli_rollout" in lerobot

    cmd_list = mgr.generate_install_command_list()
    assert len(cmd_list) >= 3
    assert any("requirements_gui.txt" in c for c in cmd_list)
    assert any("lerobot" in c for c in cmd_list)


# =============================================================================
# 4. Hardware Wizard Tests
# =============================================================================

def test_hardware_wizard_serial():
    wiz = HardwareWizard(root_dir=V4_ROOT)
    ports = wiz.list_serial_ports()
    assert isinstance(ports, list)

    # Differential snapshot test
    snap1 = wiz.take_port_snapshot()
    added, removed = wiz.diff_ports(snap1)
    assert added == []
    assert removed == []

    # Non-existent port access should safely return False
    assert wiz.test_port_access("NON_EXISTENT_PORT_9999") is False


def test_hardware_wizard_calibration_scanning(tmp_path):
    wiz = HardwareWizard(root_dir=tmp_path)

    # Create mock calibration structure
    # NOTE: LeRobot uses 'so_follower' and 'so_leader' as subfolder names in calibration cache
    f_dir = tmp_path / "calibration" / "robots" / "so_follower"
    l_dir = tmp_path / "calibration" / "teleoperators" / "so_leader"
    f_dir.mkdir(parents=True, exist_ok=True)
    l_dir.mkdir(parents=True, exist_ok=True)

    (f_dir / "custom_follower_arm.json").write_text("{}", encoding="utf-8")
    (l_dir / "custom_leader_arm.json").write_text("{}", encoding="utf-8")
    nested_f = f_dir / "robot_serial_1" / "deep"
    nested_f.mkdir(parents=True, exist_ok=True)
    (nested_f / "nested_follower.json").write_text("{}", encoding="utf-8")

    profiles = wiz.scan_calibration_profiles()
    assert "custom_follower_arm" in profiles["follower_ids"]
    assert "nested_follower" in profiles["follower_ids"]
    assert "custom_leader_arm" in profiles["leader_ids"]

    f_id, l_id = wiz.get_recommended_robot_ids()
    assert f_id == "custom_follower_arm"
    assert l_id == "custom_leader_arm"


def test_hardware_wizard_servo_scanning_and_camera_preview():
    wiz = HardwareWizard(root_dir=V4_ROOT)

    # 1. Non-existent port should return False and clear error message
    ok, alive, msg = wiz.scan_feetech_servos("NON_EXISTENT_COM_999")
    assert ok is False
    assert alive == []
    assert "Could not access" in msg or "busy" in msg or "not available" in msg

    # 2. Camera preview with gamma should return PIL Image or None without throwing
    img = wiz.capture_preview_frame(999, gamma=0.85)
    assert img is None  # Non-existent index 999 safely returns None


# =============================================================================
# 5. Process Runner Tests (Mandatory Fixes 2 and 3)
# =============================================================================

def test_calibrate_command_builder_mandatory_fix_2():
    runner = ProcessRunner(root_dir=V4_ROOT)

    # Follower calibration
    cmd_f = runner.build_calibrate_command(mode="follower", port="COM38", robot_id="my_follower")
    assert "--robot.type=so101_follower" in cmd_f, "Follower calibration MUST use --robot.type=so101_follower"
    assert "--robot.port=COM38" in cmd_f
    assert "--robot.id=my_follower" in cmd_f
    # Check that 'so_follower' is never used as CLI type
    assert not any(arg == "--robot.type=so_follower" for arg in cmd_f)

    # Leader calibration
    cmd_l = runner.build_calibrate_command(mode="leader", port="COM39", robot_id="my_leader")
    assert "--teleop.type=so101_leader" in cmd_l, "Leader calibration MUST use --teleop.type=so101_leader"
    assert "--teleop.port=COM39" in cmd_l
    assert "--teleop.id=my_leader" in cmd_l
    assert not any(arg == "--teleop.type=so_leader" for arg in cmd_l)


def test_record_command_builder_mandatory_fixes_2_and_3():
    runner = ProcessRunner(root_dir=V4_ROOT)

    cmd = runner.build_record_command(
        follower_port="COM38",
        leader_port="COM39",
        follower_id="my_follower",
        leader_id="my_leader",
        top_cam_idx=0,
        wrist_cam_idx=1,
        repo_id="voidstore/so101_pick_place",
        single_task="Pick the red block",
        num_episodes=50,
        push_to_hub=False,
        display_data=False,
    )

    # Mandatory Fix 2:
    assert "--robot.type=so101_follower" in cmd, "Record command MUST use --robot.type=so101_follower"
    assert "--teleop.type=so101_leader" in cmd, "Record command MUST use --teleop.type=so101_leader"
    assert not any(arg == "--robot.type=so_follower" for arg in cmd)
    assert not any(arg == "--teleop.type=so_leader" for arg in cmd)

    # Mandatory Fix 3:
    assert "--dataset.single_task=Pick the red block" in cmd, "Must include --dataset.single_task"
    assert "--dataset.push_to_hub=false" in cmd, "Must default to --dataset.push_to_hub=false"

    # Full camera args:
    cam_arg = next(arg for arg in cmd if arg.startswith("--robot.cameras="))
    cams_json_str = cam_arg.split("=", 1)[1]
    cams_data = json.loads(cams_json_str)
    assert cams_data["top"]["index_or_path"] == 0
    assert cams_data["wrist"]["index_or_path"] == 1
    assert cams_data["top"]["width"] == 640
    assert cams_data["top"]["fps"] == 30

    # Dataset FPS (record requires --dataset.fps, not top-level --fps)
    assert "--dataset.fps=30" in cmd
    assert not any(arg == "--fps=30" for arg in cmd), "--fps=30 causes unrecognised argument error in lerobot-record"


def test_teleoperate_command_builder_mandatory_fix_2():
    runner = ProcessRunner(root_dir=V4_ROOT)
    cmd = runner.build_teleoperate_command(
        follower_port="COM38",
        leader_port="COM39",
        follower_id="my_follower",
        leader_id="my_leader",
        fps=60,
    )
    assert "--robot.type=so101_follower" in cmd
    assert "--teleop.type=so101_leader" in cmd
    assert "--robot.port=COM38" in cmd
    assert "--teleop.port=COM39" in cmd
    assert "--fps=60" in cmd


def test_rollout_command_builder_mandatory_fixes_2_and_3():
    runner = ProcessRunner(root_dir=V4_ROOT)
    policy_path = V4_ROOT / "models" / "act_so101"

    cmd = runner.build_rollout_command(
        policy_path=policy_path,
        follower_port="COM38",
        follower_id="my_follower",
        top_cam_idx=0,
        wrist_cam_idx=1,
        task="Pick the blue cube",
        device="cuda",
        fps=30,
        interpolation_multiplier=2,
        display_data=False,
    )

    # Mandatory Fix 2:
    assert "--robot.type=so101_follower" in cmd, "Rollout MUST use --robot.type=so101_follower"
    assert not any(arg == "--robot.type=so_follower" for arg in cmd)

    # Mandatory Fix 3: full robot & camera arguments
    assert "--robot.port=COM38" in cmd
    assert "--robot.id=my_follower" in cmd
    assert "--fps=30" in cmd
    assert "--task=Pick the blue cube" in cmd

    cam_arg = next(arg for arg in cmd if arg.startswith("--robot.cameras="))
    cams_json_str = cam_arg.split("=", 1)[1]
    cams_data = json.loads(cams_json_str)
    assert cams_data["top"]["index_or_path"] == 0
    assert cams_data["wrist"]["index_or_path"] == 1
    assert cams_data["wrist"]["width"] == 640

    # Critical Architecture Rule: NEVER pass --policy.type=act with policy.path!
    assert not any(arg.startswith("--policy.type") for arg in cmd), "Must NOT pass --policy.type when --policy.path is set"
    assert any(arg.startswith("--policy.path=") for arg in cmd)

    # Smoothness & Strategy flags
    assert "--strategy.type=base" in cmd
    assert "--device=cuda" in cmd
    assert "--interpolation_multiplier=2" in cmd
    assert "--display_data=false" in cmd


def test_train_command_builder_tf32_and_amp_rules():
    runner = ProcessRunner(root_dir=V4_ROOT)

    cmd = runner.build_train_command(
        repo_id="voidstore/so101_pick_place",
        batch_size=8,
        steps=20000,
        policy_type="act",
        use_amp=False,
    )

    # Wrapper enforcing TF32
    assert any("train_act_wrapper.py" in arg for arg in cmd)
    # ACT stability rule: use_amp=false
    assert "--policy.use_amp=false" in cmd
    assert "--tf32=true" in cmd
    assert "--policy.type=act" in cmd
    assert "--batch_size=8" in cmd
    # AMP remains disabled even if a caller requests it for an ACT run.
    assert "--policy.use_amp=false" in runner.build_train_command(use_amp=True)

# =============================================================================

def test_cloud_packager_packaging(tmp_path):
    packager = CloudPackager(root_dir=tmp_path)

    # Create dummy dataset directory
    ds_dir = tmp_path / "datasets" / "test_dataset"
    ds_dir.mkdir(parents=True, exist_ok=True)
    (ds_dir / "meta.json").write_text('{"name": "test"}', encoding="utf-8")
    (ds_dir / "episodes.parquet").write_bytes(b"DATA")

    zip_path = packager.package_dataset_to_zip(ds_dir)
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"

    # Accompanying cloud bash script
    sh_script = tmp_path / "exports" / "train_test_dataset_colab.sh"
    assert sh_script.exists()
    content = sh_script.read_text(encoding="utf-8")
    assert "--policy.use_amp=false" in content
    assert "torch.set_float32_matmul_precision('high')" in content


def test_cloud_packager_model_validator(tmp_path):
    packager = CloudPackager(root_dir=tmp_path)

    # Test invalid directory
    ok, msg, _ = packager.validate_policy_directory(tmp_path / "empty_dir")
    assert ok is False

    # Create valid mock policy checkpoint
    model_dir = tmp_path / "mock_policy"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text('{"type": "act", "fps": 30}', encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"WEIGHTS")

    ok, msg, meta = packager.validate_policy_directory(model_dir)
    assert ok is True
    assert meta["policy_type"] == "act"

    # Test import to V4/models
    ok_imp, msg_imp, dest = packager.import_policy(model_dir, dest_name="imported_act_policy")
    assert ok_imp is True
    assert dest.exists()
    assert (dest / "config.json").exists()

    # Test import of deep nested zip archive (simulating cloud training output zip)
    deep_zip = tmp_path / "deep_cloud_model.zip"
    with zipfile.ZipFile(deep_zip, "w") as zf:
        zf.writestr("outputs/train/act_test/checkpoints/last/pretrained_model/config.json", '{"type": "act"}')
        zf.writestr("outputs/train/act_test/checkpoints/last/pretrained_model/model.safetensors", "WEIGHTS")

    ok_deep, msg_deep, dest_deep = packager.import_policy(deep_zip, dest_name="deep_imported_model")
    assert ok_deep is True, f"Deep nested zip import should succeed: {msg_deep}"
    assert dest_deep.exists()
    assert (dest_deep / "config.json").exists(), "Flattened target must contain config.json directly"
    assert (dest_deep / "model.safetensors").exists(), "Flattened target must contain model.safetensors"


# =============================================================================
# 7. Hardware Profile Persistence Tests
# =============================================================================

def test_hardware_profile_persistence():
    cfg_file = V4_ROOT / "config" / "hardware_profile.json"
    assert cfg_file.exists()
    data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert "follower_port" in data
    assert "leader_port" in data
    assert "follower_id" in data
    assert "leader_id" in data
    assert "top_camera_index" in data
    assert "wrist_camera_index" in data


# =============================================================================
# 8. GUI Initialization & Edge Cases Tests
# =============================================================================

def test_gui_app_initialization():
    """Verifies that the CustomTkinter StudioApp initializes all widgets without error."""
    import customtkinter as ctk
    from app_v4 import StudioApp

    app = StudioApp(root_dir=V4_ROOT)
    try:
        # Run one event loop iteration to process initial layout
        app.update_idletasks()
        app.update()

        # Check critical widgets exist
        assert hasattr(app, "tabview")
        assert hasattr(app, "combo_follower_port")
        assert hasattr(app, "combo_leader_port")
        assert hasattr(app, "combo_top_cam")
        assert hasattr(app, "combo_wrist_cam")
        assert hasattr(app, "entry_task_desc")
        assert hasattr(app, "switch_push_hub")
        assert hasattr(app, "combo_model_select")
        assert hasattr(app, "console_textbox")

        # Verify initial values match profile
        assert app.combo_follower_port.get() == app.profile.get("follower_port")
        assert app.combo_leader_port.get() == app.profile.get("leader_port")
        assert app.switch_push_hub.get() == 0  # False by default
    finally:
        app.destroy()


def test_process_runner_edge_cases():
    runner = ProcessRunner(root_dir=V4_ROOT)

    # Edge case: Task description with complex punctuation / symbols
    cmd = runner.build_rollout_command(
        policy_path="dummy/path",
        follower_port="COM38",
        task='Pick "red" & (blue) objects; don\'t drop!',
    )
    task_arg = next(arg for arg in cmd if arg.startswith("--task="))
    assert "Pick \"red\" & (blue) objects; don't drop!" in task_arg

    # Test process termination returns safely
    assert runner.terminate_active_processes() == 0

    # Test CLI binary resolution
    cli_bin = runner.get_cli_bin("lerobot-record")
    assert "lerobot-record" in cli_bin

    # Test terminal launch and termination
    proc = runner.run_command_in_terminal([sys.executable, "-c", "import time; time.sleep(10)"], window_title="TestWindow")
    assert proc is not None
    # Terminate should clean up the process
    stopped = runner.terminate_active_processes()
    assert stopped >= 1

