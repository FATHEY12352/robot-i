"""
SO-101 Robotics Studio V4 — All-in-One Desktop GUI Application.
Built with CustomTkinter for student-friendly teleoperation, ACT training, and autonomous policy rollout.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError as e:
    print(f"[ERROR] Required GUI packages not found: {e}")
    print("Please run start_v4.bat or install requirements_gui.txt")
    sys.exit(1)

from core.logger import get_logger, StudioLogger
from core.env_manager import EnvManager
from core.hardware_wizard import HardwareWizard
from core.process_runner import ProcessRunner
from core.cloud_packager import CloudPackager


class StudioApp(ctk.CTk):
    """Main application window for SO-101 Robotics Studio V4."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        super().__init__()

        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parent
        else:
            self.root_dir = Path(root_dir)

        # Core subsystems
        self.logger = get_logger("StudioApp")
        self.env_mgr = EnvManager(self.root_dir)
        self.hw_wizard = HardwareWizard(self.root_dir)
        self.runner = ProcessRunner(self.root_dir)
        self.packager = CloudPackager(self.root_dir)

        # Hardware profile
        self.config_file = self.root_dir / "config" / "hardware_profile.json"
        self.profile = self.load_hardware_profile()

        # Port snapshot for differential scan & model map
        self._port_snapshot = set()
        self._available_models_map: Dict[str, str] = {}

        # Image persistence references to prevent Tkinter "pyimage does not exist" garbage collection bugs
        self._active_images: Dict[str, Any] = {}
        self._preview_generation: Dict[str, int] = {"Top": 0, "Wrist": 0}
        self._blank_placeholder = ctk.CTkImage(
            light_image=Image.new("RGB", (210, 160), color="#0f172a"),
            dark_image=Image.new("RGB", (210, 160), color="#0f172a"),
            size=(210, 160),
        )

        # Window appearance
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.title("SO-101 Robotics Studio V4 — LeRobot ACT Edition")
        self.geometry("1180x820")
        self.minsize(980, 720)

        # Build UI layout
        self._build_header()
        self._build_main_tabs()
        self._build_console_panel()

        # Connect logger to GUI console
        self.logger.subscribe(self._on_log_message)

        # Initial background hardware & env probe
        self.after(200, self._initial_probe)

    # -------------------------------------------------------------------------
    # Profile Persistence
    # -------------------------------------------------------------------------

    def load_hardware_profile(self) -> Dict[str, Any]:
        """Loads saved hardware settings or returns sane defaults."""
        defaults = {
            "follower_port": "COM38",
            "leader_port": "COM39",
            "follower_id": "my_follower",
            "leader_id": "my_leader",
            "top_camera_index": 0,
            "wrist_camera_index": 1,
            "camera_width": 640,
            "camera_height": 480,
            "fps": 30,
            "display_data": False,
            "device": "cuda",
            "interpolation_multiplier": 2,
            "dataset_name": "so101_pick_place",
            "single_task": "Pick the target object and place it into the container",
            "batch_size": 8,
            "train_steps": 20000,
            "save_freq": 5000,
            "use_amp": False,
            "tf32": True,
        }
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                defaults.update(data)
            except Exception as e:
                self.logger.warning(f"Could not parse hardware_profile.json: {e}")
        return defaults

    def save_hardware_profile(self) -> None:
        """Saves current GUI values into hardware_profile.json."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.config_file.write_text(json.dumps(self.profile, indent=2), encoding="utf-8")
            self.logger.info(f"Hardware profile saved to {self.config_file}")
            self.status_label.configure(text="Status: Hardware Profile Saved", text_color="#2ecc71")
        except Exception as e:
            self.logger.error(f"Failed to save profile: {e}")
            self.status_label.configure(text=f"Error saving profile: {e}", text_color="#e74c3c")

    # -------------------------------------------------------------------------
    # GUI Construction
    # -------------------------------------------------------------------------

    def destroy(self) -> None:
        """Cleanup logger listener and window resources on close."""
        try:
            self.logger.unsubscribe(self._on_log_message)
        except Exception:
            pass
        super().destroy()

    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#1f242d")
        header_frame.pack(fill="x", padx=14, pady=(12, 6))

        # Title and subtitle
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=14, pady=10)

        ctk.CTkLabel(
            title_box,
            text="SO-101 ROBOTICS STUDIO V4",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Hugging Face LeRobot & ACT Autonomous Manipulation System",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
        ).pack(anchor="w")

        # Badges on right side
        self.badges_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.badges_frame.pack(side="right", padx=14, pady=10)

        self.badge_os = ctk.CTkLabel(
            self.badges_frame,
            text=f"OS: {platform.system()}",
            fg_color="#334155",
            corner_radius=6,
            padx=8,
            pady=4,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.badge_os.pack(side="left", padx=4)

        self.badge_gpu = ctk.CTkLabel(
            self.badges_frame,
            text="GPU: Probing...",
            fg_color="#334155",
            corner_radius=6,
            padx=8,
            pady=4,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.badge_gpu.pack(side="left", padx=4)

        self.badge_lerobot = ctk.CTkLabel(
            self.badges_frame,
            text="LeRobot: Checking...",
            fg_color="#334155",
            corner_radius=6,
            padx=8,
            pady=4,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.badge_lerobot.pack(side="left", padx=4)

    def _build_main_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=6)

        self.tab_hw = self.tabview.add("1. Hardware Wizard & Calibration")
        self.tab_rec = self.tabview.add("2. Data Collection (Record)")
        self.tab_train = self.tabview.add("3. Training & Cloud Sync")
        self.tab_rollout = self.tabview.add("4. Autonomous Rollout")

        self._build_tab_hardware()
        self._build_tab_record()
        self._build_tab_train()
        self._build_tab_rollout()

    # -------------------------------------------------------------------------
    # TAB 1: Hardware Wizard & Calibration
    # -------------------------------------------------------------------------

    def _build_tab_hardware(self) -> None:
        # 2-column layout: Left = Serial & Calibration, Right = Dual Cameras & Live Preview
        left_col = ctk.CTkFrame(self.tab_hw, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        right_col = ctk.CTkFrame(self.tab_hw, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=8, pady=8)

        # --- Section 1: Serial COM Ports ---
        serial_card = ctk.CTkFrame(left_col, corner_radius=8)
        serial_card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            serial_card,
            text="1. Serial Bus Arms (Feetech STS3215)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # Follower Arm
        f_row = ctk.CTkFrame(serial_card, fg_color="transparent")
        f_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(f_row, text="Follower Port:", width=110, anchor="w").pack(side="left")
        self.combo_follower_port = ctk.CTkComboBox(f_row, values=["COM38", "COM3", "COM4", "/dev/ttyUSB0"], width=130)
        self.combo_follower_port.set(self.profile.get("follower_port", "COM38"))
        self.combo_follower_port.pack(side="left", padx=4)
        ctk.CTkLabel(f_row, text="ID:", width=30).pack(side="left", padx=2)
        self.entry_follower_id = ctk.CTkEntry(f_row, width=120)
        self.entry_follower_id.insert(0, self.profile.get("follower_id", "my_follower"))
        self.entry_follower_id.pack(side="left", padx=4)
        ctk.CTkButton(f_row, text="Test", width=55, command=self._test_follower_port).pack(side="left", padx=4)

        # Leader Arm
        l_row = ctk.CTkFrame(serial_card, fg_color="transparent")
        l_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(l_row, text="Leader Port:", width=110, anchor="w").pack(side="left")
        self.combo_leader_port = ctk.CTkComboBox(l_row, values=["COM39", "COM5", "COM6", "/dev/ttyUSB1"], width=130)
        self.combo_leader_port.set(self.profile.get("leader_port", "COM39"))
        self.combo_leader_port.pack(side="left", padx=4)
        ctk.CTkLabel(l_row, text="ID:", width=30).pack(side="left", padx=2)
        self.entry_leader_id = ctk.CTkEntry(l_row, width=120)
        self.entry_leader_id.insert(0, self.profile.get("leader_id", "my_leader"))
        self.entry_leader_id.pack(side="left", padx=4)
        ctk.CTkButton(l_row, text="Test", width=55, command=self._test_leader_port).pack(side="left", padx=4)

        # Action buttons row: Differential, Refresh, Swap, Free Ports
        action_row = ctk.CTkFrame(serial_card, fg_color="transparent")
        action_row.pack(fill="x", padx=12, pady=(6, 10))
        ctk.CTkButton(
            action_row,
            text="Detect Plugged Port",
            command=self._differential_port_scan,
            width=130,
            fg_color="#0284c7",
            hover_color="#0369a1",
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            action_row,
            text="Refresh Ports",
            width=85,
            command=self._refresh_serial_ports,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            action_row,
            text="Swap Ports",
            width=75,
            command=self._swap_ports,
            fg_color="#475569",
            hover_color="#334155",
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            action_row,
            text="Free Ports",
            width=75,
            command=self._kill_background_processes,
            fg_color="#dc2626",
            hover_color="#b91c1c",
        ).pack(side="left", padx=2)

        # --- Section 2: Calibration Store ---
        calib_card = ctk.CTkFrame(left_col, corner_radius=8)
        calib_card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            calib_card,
            text="2. Calibration Status (LeRobot Store)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.label_calib_status = ctk.CTkLabel(
            calib_card,
            text="Scanning calibration cache...",
            text_color="#94a3b8",
            wraplength=460,
            justify="left",
        )
        self.label_calib_status.pack(anchor="w", padx=12, pady=4)

        calib_btns = ctk.CTkFrame(calib_card, fg_color="transparent")
        calib_btns.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkButton(
            calib_btns,
            text="Calibrate Follower Arm",
            command=self._launch_calibrate_follower,
            fg_color="#f59e0b",
            hover_color="#d97706",
        ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(
            calib_btns,
            text="Calibrate Leader Arm",
            command=self._launch_calibrate_leader,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
        ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(
            calib_btns,
            text="Test Live Teleop",
            command=self._launch_teleoperate,
            fg_color="#06b6d4",
            hover_color="#0891b2",
        ).pack(side="left", fill="x", expand=True, padx=4)

        # Save profile button
        ctk.CTkButton(
            left_col,
            text="Save Current Hardware Profile",
            command=self._sync_and_save_profile,
            fg_color="#10b981",
            hover_color="#059669",
        ).pack(fill="x", pady=10)

        # --- Right Column: Dual Cameras & Preview ---
        cam_card = ctk.CTkFrame(right_col, corner_radius=8)
        cam_card.pack(fill="both", expand=True, pady=6)

        ctk.CTkLabel(
            cam_card,
            text="3. Dual Cameras (Top & Wrist at 640x480 @ 30fps)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # Camera selectors and preview buttons
        cam_ctrls = ctk.CTkFrame(cam_card, fg_color="transparent")
        cam_ctrls.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(cam_ctrls, text="Top:").pack(side="left")
        self.combo_top_cam = ctk.CTkComboBox(cam_ctrls, values=["0", "1", "2", "3"], width=55)
        self.combo_top_cam.set(str(self.profile.get("top_camera_index", 0)))
        self.combo_top_cam.pack(side="left", padx=2)
        ctk.CTkButton(cam_ctrls, text="Top", width=45, command=self._preview_top_camera).pack(side="left", padx=2)

        ctk.CTkLabel(cam_ctrls, text="Wrist:", padx=4).pack(side="left")
        self.combo_wrist_cam = ctk.CTkComboBox(cam_ctrls, values=["0", "1", "2", "3"], width=55)
        self.combo_wrist_cam.set(str(self.profile.get("wrist_camera_index", 1)))
        self.combo_wrist_cam.pack(side="left", padx=2)
        ctk.CTkButton(cam_ctrls, text="Wrist", width=45, command=self._preview_wrist_camera).pack(side="left", padx=2)

        ctk.CTkButton(cam_ctrls, text="Preview Both", width=85, fg_color="#0284c7", command=self._preview_both_cameras).pack(side="left", padx=4)

        # Anti-glare / Exposure Tone-Down check
        anti_glare_row = ctk.CTkFrame(cam_card, fg_color="transparent")
        anti_glare_row.pack(fill="x", padx=12, pady=(2, 6))
        self.check_darken = ctk.CTkCheckBox(
            anti_glare_row,
            text="Tone Down Glare / Balanced Exposure (Anti-Washed)",
            font=ctk.CTkFont(size=12),
        )
        self.check_darken.select()
        self.check_darken.pack(side="left")

        # Dual Viewports Frame (side by side)
        views_frame = ctk.CTkFrame(cam_card, fg_color="transparent")
        views_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # Top viewport box
        top_box = ctk.CTkFrame(views_frame, fg_color="#0f172a", corner_radius=8)
        top_box.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(top_box, text="Top Workspace Cam", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=6, pady=2)
        self.preview_top_canvas = ctk.CTkLabel(
            top_box,
            text="[ Top Camera ]\nClick 'Top' above",
            width=210,
            height=180,
            fg_color="transparent",
        )
        self.preview_top_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Wrist viewport box
        wrist_box = ctk.CTkFrame(views_frame, fg_color="#0f172a", corner_radius=8)
        wrist_box.pack(side="right", fill="both", expand=True, padx=3)
        ctk.CTkLabel(wrist_box, text="Wrist / Gripper Cam", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(anchor="w", padx=6, pady=2)
        self.preview_wrist_canvas = ctk.CTkLabel(
            wrist_box,
            text="[ Wrist Camera ]\nClick 'Wrist' above",
            width=210,
            height=180,
            fg_color="transparent",
        )
        self.preview_wrist_canvas.pack(fill="both", expand=True, padx=4, pady=4)

    # -------------------------------------------------------------------------
    # TAB 2: Data Collection (Record)
    # -------------------------------------------------------------------------

    def _build_tab_record(self) -> None:
        rec_card = ctk.CTkFrame(self.tab_rec, corner_radius=8)
        rec_card.pack(fill="both", expand=True, padx=14, pady=10)

        ctk.CTkLabel(
            rec_card,
            text="Teleoperated Dataset Recording (lerobot-record)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Single task description (Mandatory Fix 3)
        ctk.CTkLabel(rec_card, text="Single Task Description (Embedded into Dataset):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(6, 2))
        self.entry_task_desc = ctk.CTkEntry(rec_card, placeholder_text="e.g. Pick the blue cube and place it into the white tray")
        self.entry_task_desc.insert(0, self.profile.get("single_task", "Pick the target object and place it into the container"))
        self.entry_task_desc.pack(fill="x", padx=14, pady=4)

        # Dataset name / Repo ID
        meta_row = ctk.CTkFrame(rec_card, fg_color="transparent")
        meta_row.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(meta_row, text="Dataset Identifier (repo_id):").pack(side="left")
        self.entry_repo_id = ctk.CTkEntry(meta_row, width=280)
        self.entry_repo_id.insert(0, f"voidstore/{self.profile.get('dataset_name', 'so101_pick_place')}")
        self.entry_repo_id.pack(side="left", padx=8)

        ctk.CTkLabel(meta_row, text="Num Episodes:").pack(side="left", padx=(10, 2))
        self.entry_num_episodes = ctk.CTkEntry(meta_row, width=70)
        self.entry_num_episodes.insert(0, "50")
        self.entry_num_episodes.pack(side="left", padx=4)

        # Flags: Push to Hub & Display Data
        flags_row = ctk.CTkFrame(rec_card, fg_color="transparent")
        flags_row.pack(fill="x", padx=14, pady=8)

        self.switch_push_hub = ctk.CTkSwitch(flags_row, text="Push to Hugging Face Hub (default: False)")
        # Default is False per Mandatory Fix 3
        self.switch_push_hub.pack(side="left", padx=10)

        self.switch_display_data_rec = ctk.CTkSwitch(flags_row, text="Display Data / Rerun Viewer")
        self.switch_display_data_rec.pack(side="left", padx=10)

        # Action Buttons
        btn_row = ctk.CTkFrame(rec_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=16)

        ctk.CTkButton(
            btn_row,
            text="START RECORDING EPISODES",
            command=self._launch_record,
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_row,
            text="Open Datasets Folder",
            command=self._open_datasets_dir,
            height=40,
        ).pack(side="left", padx=6)

        # Info Box
        info_frame = ctk.CTkFrame(rec_card, fg_color="#0f172a", corner_radius=6)
        info_frame.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(
            info_frame,
            text="Note: When you click START RECORDING, an interactive console window opens.\n"
                 "Follow the audio and terminal prompts: Move the leader arm to manipulate the follower.\n"
                 "Press Enter/Space to complete each episode, or Ctrl+C to stop recording.",
            justify="left",
            text_color="#94a3b8",
            padx=12,
            pady=8,
        ).pack(anchor="w")

    # -------------------------------------------------------------------------
    # TAB 3: Training & Cloud Sync
    # -------------------------------------------------------------------------

    def _build_tab_train(self) -> None:
        train_card = ctk.CTkFrame(self.tab_train, corner_radius=8)
        train_card.pack(fill="both", expand=True, padx=14, pady=10)

        ctk.CTkLabel(
            train_card,
            text="ACT Policy Training & Cloud Acceleration",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Local Training Section
        loc_frame = ctk.CTkFrame(train_card, corner_radius=6)
        loc_frame.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(loc_frame, text="A. Local GPU ACT Policy Training", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        params_row = ctk.CTkFrame(loc_frame, fg_color="transparent")
        params_row.pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(params_row, text="Steps:").pack(side="left")
        self.entry_train_steps = ctk.CTkEntry(params_row, width=80)
        self.entry_train_steps.insert(0, "20000")
        self.entry_train_steps.pack(side="left", padx=4)

        ctk.CTkLabel(params_row, text="Batch Size:").pack(side="left", padx=(10, 2))
        self.entry_train_batch = ctk.CTkEntry(params_row, width=60)
        self.entry_train_batch.insert(0, "8")
        self.entry_train_batch.pack(side="left", padx=4)

        ctk.CTkLabel(params_row, text="Precision: TF32 High (AMP Disabled for ACT)", text_color="#22c55e").pack(side="left", padx=14)

        ctk.CTkButton(
            loc_frame,
            text="Train ACT Policy Locally",
            command=self._launch_local_training,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
        ).pack(anchor="w", padx=10, pady=(4, 10))

        # Cloud Export Section
        cloud_frame = ctk.CTkFrame(train_card, corner_radius=6)
        cloud_frame.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(cloud_frame, text="B. Cloud GPU Training Packager (Colab / RunPod / Kaggle)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        c_row = ctk.CTkFrame(cloud_frame, fg_color="transparent")
        c_row.pack(fill="x", padx=10, pady=(4, 10))

        ctk.CTkButton(
            c_row,
            text="Export Dataset Zip for Cloud",
            command=self._package_for_cloud,
            fg_color="#0284c7",
            hover_color="#0369a1",
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            c_row,
            text="Open Exports Folder",
            command=self._open_exports_dir,
        ).pack(side="left", padx=4)

        # Model Checkpoint Importer Section
        imp_frame = ctk.CTkFrame(train_card, corner_radius=6)
        imp_frame.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(imp_frame, text="C. Import & Validate Trained Policy Checkpoint", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        i_row = ctk.CTkFrame(imp_frame, fg_color="transparent")
        i_row.pack(fill="x", padx=10, pady=(4, 10))

        ctk.CTkButton(
            i_row,
            text="Import Model Archive (.zip or folder)",
            command=self._import_model_checkpoint,
            fg_color="#10b981",
            hover_color="#059669",
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            i_row,
            text="Open Models Folder",
            command=self._open_models_dir,
        ).pack(side="left", padx=4)

    # -------------------------------------------------------------------------
    # TAB 4: Autonomous Deployment (Rollout)
    # -------------------------------------------------------------------------

    def _build_tab_rollout(self) -> None:
        rollout_card = ctk.CTkFrame(self.tab_rollout, corner_radius=8)
        rollout_card.pack(fill="both", expand=True, padx=14, pady=10)

        ctk.CTkLabel(
            rollout_card,
            text="Autonomous Policy Rollout & Inference (lerobot-rollout)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Model Selector
        m_row = ctk.CTkFrame(rollout_card, fg_color="transparent")
        m_row.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(m_row, text="Select Trained Model Checkpoint:").pack(side="left")
        self.combo_model_select = ctk.CTkComboBox(m_row, values=["None found"], width=380)
        self.combo_model_select.pack(side="left", padx=8)
        ctk.CTkButton(m_row, text="Refresh Models", width=110, command=self._refresh_available_models).pack(side="left", padx=4)

        # Task Prompt
        ctk.CTkLabel(rollout_card, text="Task Prompt (passed to policy):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(6, 2))
        self.entry_rollout_task = ctk.CTkEntry(rollout_card)
        self.entry_rollout_task.insert(0, self.profile.get("single_task", "Pick the target object and place it into the container"))
        self.entry_rollout_task.pack(fill="x", padx=14, pady=4)

        # Device & Smoothness Flags
        opt_row = ctk.CTkFrame(rollout_card, fg_color="transparent")
        opt_row.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(opt_row, text="Inference Device:").pack(side="left")
        self.combo_device = ctk.CTkComboBox(opt_row, values=["cuda", "cpu"], width=80)
        self.combo_device.set(self.profile.get("device", "cuda"))
        self.combo_device.pack(side="left", padx=6)

        ctk.CTkLabel(opt_row, text="Interpolation Multiplier:").pack(side="left", padx=(10, 2))
        self.entry_interp = ctk.CTkEntry(opt_row, width=50)
        self.entry_interp.insert(0, "2")
        self.entry_interp.pack(side="left", padx=4)

        self.switch_display_data_rollout = ctk.CTkSwitch(opt_row, text="Display Data (Rerun Debug Viewer)")
        self.switch_display_data_rollout.pack(side="left", padx=14)

        # Big Launch Buttons
        act_row = ctk.CTkFrame(rollout_card, fg_color="transparent")
        act_row.pack(fill="x", padx=14, pady=20)

        ctk.CTkButton(
            act_row,
            text="DEPLOY AUTONOMOUS ROLLOUT",
            command=self._launch_rollout,
            fg_color="#10b981",
            hover_color="#059669",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            act_row,
            text="EMERGENCY STOP / ABORT",
            command=self._emergency_stop,
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left", padx=8)

    # -------------------------------------------------------------------------
    # Bottom Console & Status Bar
    # -------------------------------------------------------------------------

    def _build_console_panel(self) -> None:
        console_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#181c24")
        console_frame.pack(fill="x", padx=14, pady=(4, 10))

        bar_row = ctk.CTkFrame(console_frame, fg_color="transparent")
        bar_row.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(bar_row, text="System Log Output:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(side="left")
        self.status_label = ctk.CTkLabel(bar_row, text="Status: Ready", text_color="#38bdf8", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left", padx=20)

        ctk.CTkButton(bar_row, text="Clear Console", width=90, height=22, command=self._clear_console).pack(side="right")

        self.console_textbox = ctk.CTkTextbox(console_frame, height=130, font=ctk.CTkFont(family="Consolas", size=11))
        self.console_textbox.pack(fill="both", expand=True, padx=10, pady=(4, 8))

    def _on_log_message(self, level_name: str, level_no: int, formatted: str) -> None:
        """Callback from StudioLogger to append messages in thread-safe manner."""
        def _append():
            try:
                if self.winfo_exists():
                    self.console_textbox.insert("end", formatted + "\n")
                    self.console_textbox.see("end")
            except Exception:
                pass
        try:
            if self.winfo_exists():
                self.after(0, _append)
        except Exception:
            pass

    def _clear_console(self) -> None:
        self.console_textbox.delete("1.0", "end")

    # -------------------------------------------------------------------------
    # Background Probing & Event Handlers
    # -------------------------------------------------------------------------

    def _initial_probe(self) -> None:
        """Probes hardware and environment upon startup in non-blocking thread."""
        def _worker():
            try:
                env_sum = self.env_mgr.get_env_summary()
            except Exception as e:
                self.logger.warning(f"Initial environment probe failed: {e}")
                return
            gpu = env_sum["gpu"]
            lerobot_stat = env_sum["lerobot"]

            # Update badges
            def _update_ui():
                try:
                    if not self.winfo_exists():
                        return
                    if gpu["cuda_available"]:
                        self.badge_gpu.configure(text=f"GPU: {gpu['device_name']} ({gpu['vram_gb']}GB)", fg_color="#15803d")
                    else:
                        self.badge_gpu.configure(text="GPU: CPU Mode", fg_color="#b45309")

                    if lerobot_stat["installed"]:
                        self.badge_lerobot.configure(text=f"LeRobot: {lerobot_stat['version']}", fg_color="#15803d")
                    else:
                        self.badge_lerobot.configure(text="LeRobot: Not Found", fg_color="#b91c1c")
                except Exception:
                    pass

            try:
                if self.winfo_exists():
                    self.after(0, _update_ui)
            except Exception:
                pass

            # Discover ports and local metadata off the Tk main thread, but apply widgets on it.
            try:
                ports = self.hw_wizard.get_port_names()
                profiles = self.hw_wizard.scan_calibration_profiles()
                models = self.packager.list_available_models()

                def _update_discovery_ui():
                    try:
                        if not self.winfo_exists():
                            return
                        self._apply_serial_ports(ports)
                        self._apply_calibration_profiles(profiles)
                        self._apply_available_models(models)
                    except Exception as e:
                        self.logger.debug(f"Discovery UI update exception: {e}")

                self.after(0, _update_discovery_ui)
            except Exception as e:
                self.logger.warning(f"Initial hardware discovery failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_serial_ports(self, ports: List[str]) -> None:
        """Apply discovered serial ports from the Tk main thread only."""
        if not ports:
            ports = ["No Ports Found"]
        self.combo_follower_port.configure(values=ports)
        self.combo_leader_port.configure(values=ports)
        cur_f = self.combo_follower_port.get()
        cur_l = self.combo_leader_port.get()
        if len(ports) >= 2:
            if cur_f not in ports:
                self.combo_follower_port.set(ports[0])
            if cur_l not in ports:
                self.combo_leader_port.set(ports[1])
        elif len(ports) == 1 and ports[0] != "No Ports Found" and cur_f not in ports:
            self.combo_follower_port.set(ports[0])
        self.logger.info(f"Available serial ports updated: {ports}")

    def _refresh_serial_ports(self) -> None:
        """Discover serial ports in a worker and update comboboxes safely."""
        def _worker():
            try:
                ports = self.hw_wizard.get_port_names()
                self.after(0, lambda: self._apply_serial_ports(ports))
            except Exception as e:
                self.logger.warning(f"Serial port refresh failed: {e}")
        threading.Thread(target=_worker, daemon=True).start()

    def _apply_calibration_profiles(self, profiles: Dict[str, List[str]]) -> None:
        f_ids = profiles["follower_ids"]
        l_ids = profiles["leader_ids"]
        msg = f"Calibration Store found: Follower IDs: {f_ids or ['None']}, Leader IDs: {l_ids or ['None']}"
        self.label_calib_status.configure(text=msg)
        self.logger.info(msg)
        if f_ids and not self.entry_follower_id.get():
            self.entry_follower_id.delete(0, "end")
            self.entry_follower_id.insert(0, f_ids[0])
        if l_ids and not self.entry_leader_id.get():
            self.entry_leader_id.delete(0, "end")
            self.entry_leader_id.insert(0, l_ids[0])

    def _apply_available_models(self, models: List[Dict[str, Any]]) -> None:
        self._available_models_map.clear()
        model_names = []
        for m in models:
            label = f"{m['name']} ({m['path']})"
            self._available_models_map[label] = m["path"]
            model_names.append(label)
        if not model_names:
            model_names = ["No Models Found"]
            self._available_models_map["No Models Found"] = ""
        self.combo_model_select.configure(values=model_names)
        self.combo_model_select.set(model_names[0])
        self.logger.info(f"Available policy models: {model_names}")

    def _refresh_available_models(self) -> None:
        """Scan policy folders in a worker and update the selector on Tk's thread."""
        def _worker():
            try:
                models = self.packager.list_available_models()
                self.after(0, lambda: self._apply_available_models(models))
            except Exception as e:
                self.logger.warning(f"Model refresh failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _check_calibration_store(self) -> None:
        """Scan calibration storage in a worker and update the label on Tk's thread."""
        def _worker():
            try:
                profiles = self.hw_wizard.scan_calibration_profiles()
                self.after(0, lambda: self._apply_calibration_profiles(profiles))
            except Exception as e:
                self.logger.warning(f"Calibration scan failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _swap_ports(self) -> None:
        """Swaps follower and leader ports with 1 click."""
        f_port = self.combo_follower_port.get()
        l_port = self.combo_leader_port.get()
        self.combo_follower_port.set(l_port)
        self.combo_leader_port.set(f_port)
        msg = f"Swapped: Follower={l_port}, Leader={f_port}"
        self.status_label.configure(text=f"Status: {msg}", text_color="#38bdf8")
        self.logger.info(msg)

    def _kill_background_processes(self) -> None:
        """Kills any orphaned LeRobot/Python subprocesses to immediately release locked COM ports."""
        self.runner.terminate_active_processes()
        # The runner tracks launched process trees; Windows taskkill does not support wildcards with /IM.
        msg = "Terminated tracked studio processes. Serial ports should now be available."
        self.status_label.configure(text=f"Status: {msg}", text_color="#22c55e")
        self.logger.info(msg)

    def _differential_port_scan(self) -> None:
        """Guides user to discover new COM port after plugging in."""
        self._port_snapshot = self.hw_wizard.take_port_snapshot()
        self.logger.info("Snapshotted current ports. Please plug in or unplug your USB adapter, then click OK.")
        self.status_label.configure(text="Status: Waiting for USB cable event...", text_color="#f59e0b")

        def _check_diff():
            def _apply_diff(added: List[str], removed: List[str]) -> None:
                if added:
                    self.logger.info(f"[+] Detected newly connected port(s): {added}")
                    self.status_label.configure(text=f"Detected Port: {added[0]}", text_color="#22c55e")
                    self._refresh_serial_ports()
                    self.combo_follower_port.set(added[0])
                elif removed:
                    self.logger.info(f"[-] Detected disconnected port(s): {removed}")
                    self._refresh_serial_ports()
                else:
                    self.logger.info("No port change detected.")
                    self.status_label.configure(text="Status: No port change detected", text_color="#94a3b8")

            def _worker():
                try:
                    added, removed = self.hw_wizard.diff_ports(self._port_snapshot)
                    self.after(0, lambda: _apply_diff(added, removed))
                except Exception as e:
                    self.logger.warning(f"Differential port scan failed: {e}")

            threading.Thread(target=_worker, daemon=True).start()

        self.after(3000, _check_diff)

    def _test_follower_port(self) -> None:
        """Tests follower port by pinging STS3215 servos 1-6."""
        port = self.combo_follower_port.get()
        self.status_label.configure(text=f"Status: Pinging servos on Follower {port}...", text_color="#f59e0b")

        def _worker():
            ok, alive, msg = self.hw_wizard.scan_feetech_servos(port)
            color = "#22c55e" if ok else "#ef4444"
            def _update():
                if self.winfo_exists():
                    self.status_label.configure(text=f"Follower ({port}): {msg}", text_color=color)
            self.after(0, _update)
            self.logger.info(f"Follower ({port}): {msg}")

        threading.Thread(target=_worker, daemon=True).start()

    def _test_leader_port(self) -> None:
        """Tests leader port by pinging STS3215 servos 1-6."""
        port = self.combo_leader_port.get()
        self.status_label.configure(text=f"Status: Pinging servos on Leader {port}...", text_color="#f59e0b")

        def _worker():
            ok, alive, msg = self.hw_wizard.scan_feetech_servos(port)
            color = "#22c55e" if ok else "#ef4444"
            def _update():
                if self.winfo_exists():
                    self.status_label.configure(text=f"Leader ({port}): {msg}", text_color=color)
            self.after(0, _update)
            self.logger.info(f"Leader ({port}): {msg}")

        threading.Thread(target=_worker, daemon=True).start()

    def _check_calibration_store(self) -> None:
        """Scan calibration storage in a worker and update the label on Tk's thread."""
        def _worker():
            try:
                profiles = self.hw_wizard.scan_calibration_profiles()
                self.after(0, lambda: self._apply_calibration_profiles(profiles))
            except Exception as e:
                self.logger.warning(f"Calibration scan failed: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _preview_top_camera(self) -> None:
        try:
            idx = self._safe_int(self.combo_top_cam.get(), 0, 0)
            self._async_preview(idx, self.preview_top_canvas, "Top")
        except Exception as e:
            self.logger.warning(f"Top camera preview could not start: {e}")

    def _preview_wrist_camera(self) -> None:
        try:
            idx = self._safe_int(self.combo_wrist_cam.get(), 1, 0)
            self._async_preview(idx, self.preview_wrist_canvas, "Wrist")
        except Exception as e:
            self.logger.warning(f"Wrist camera preview could not start: {e}")

    def _preview_both_cameras(self) -> None:
        self._preview_top_camera()
        self._preview_wrist_camera()

    def _async_preview(self, cam_idx: int, target_label: ctk.CTkLabel, name: str) -> None:
        """Capture one frame asynchronously, with stale-result and camera-timeout protection."""
        self._preview_generation[name] = self._preview_generation.get(name, 0) + 1
        generation = self._preview_generation[name]
        try:
            target_label.configure(image=self._blank_placeholder, text=f"Capturing {name} Cam {cam_idx}...")
        except Exception:
            return

        gamma = 0.85 if getattr(self, "check_darken", None) and self.check_darken.get() else 1.0

        def _worker():
            img = self.hw_wizard.capture_preview_frame(
                cam_idx,
                target_width=210,
                target_height=160,
                warmup_frames=8,
                gamma=gamma,
                open_timeout=2.0,
            )

            def _update_ui():
                try:
                    if not self.winfo_exists() or self._preview_generation.get(name) != generation:
                        return
                    if img is not None:
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(210, 160))
                        self._active_images[name] = ctk_img
                        target_label.configure(image=ctk_img, text="")
                        self.logger.info(f"Captured live preview from {name} Camera {cam_idx}")
                    else:
                        target_label.configure(image=self._blank_placeholder, text=f"Could not open\n{name} Cam {cam_idx}!")
                        self.logger.warning(f"Could not open {name} Camera {cam_idx}")
                except Exception as e:
                    self.logger.debug(f"UI preview update exception: {e}")
            try:
                self.after(0, _update_ui)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _preview_camera(self, cam_idx: int) -> None:
        """Backward compatibility wrapper for preview."""
        self._preview_top_camera()

    def _safe_int(self, raw: Any, default: int, minimum: Optional[int] = None) -> int:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            return default
        return max(value, minimum) if minimum is not None else value

    def _sync_and_save_profile(self) -> None:
        self.profile["follower_port"] = self.combo_follower_port.get()
        self.profile["leader_port"] = self.combo_leader_port.get()
        self.profile["follower_id"] = self.entry_follower_id.get()
        self.profile["leader_id"] = self.entry_leader_id.get()
        self.profile["top_camera_index"] = self._safe_int(self.combo_top_cam.get(), 0, 0)
        self.profile["wrist_camera_index"] = self._safe_int(self.combo_wrist_cam.get(), 1, 0)
        self.profile["single_task"] = self.entry_task_desc.get()
        self.profile["device"] = self.combo_device.get()
        self.save_hardware_profile()

    # -------------------------------------------------------------------------
    # Launchers for LeRobot Operations
    # -------------------------------------------------------------------------

    def _launch_calibrate_follower(self) -> None:
        port = self.combo_follower_port.get()
        robot_id = self.entry_follower_id.get()
        cmd = self.runner.build_calibrate_command(mode="follower", port=port, robot_id=robot_id)
        self.logger.info(f"Launching Follower calibration: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot Calibrate Follower")

    def _launch_calibrate_leader(self) -> None:
        port = self.combo_leader_port.get()
        leader_id = self.entry_leader_id.get()
        cmd = self.runner.build_calibrate_command(mode="leader", port=port, robot_id=leader_id)
        self.logger.info(f"Launching Leader calibration: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot Calibrate Leader")

    def _launch_teleoperate(self) -> None:
        cmd = self.runner.build_teleoperate_command(
            follower_port=self.combo_follower_port.get(),
            leader_port=self.combo_leader_port.get(),
            follower_id=self.entry_follower_id.get(),
            leader_id=self.entry_leader_id.get(),
            fps=self._safe_int(self.profile.get("fps", 60), 60, 1),
        )
        self.logger.info(f"Launching Live Teleoperation: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot Live Teleoperation")

    def _launch_record(self) -> None:
        repo_id = self.entry_repo_id.get().strip()
        single_task = self.entry_task_desc.get().strip()
        num_ep = self._safe_int(self.entry_num_episodes.get() or "50", 50, 1)
        top_camera = self._safe_int(self.combo_top_cam.get(), 0, 0)
        wrist_camera = self._safe_int(self.combo_wrist_cam.get(), 1, 0)
        push_hub = bool(self.switch_push_hub.get())
        display_data = bool(self.switch_display_data_rec.get())

        cmd = self.runner.build_record_command(
            follower_port=self.combo_follower_port.get(),
            leader_port=self.combo_leader_port.get(),
            follower_id=self.entry_follower_id.get(),
            leader_id=self.entry_leader_id.get(),
            top_cam_idx=top_camera,
            wrist_cam_idx=wrist_camera,
            repo_id=repo_id,
            single_task=single_task,
            num_episodes=num_ep,
            push_to_hub=push_hub,
            display_data=display_data,
        )
        self.logger.info(f"Launching LeRobot record: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot Record Episodes")

    def _launch_local_training(self) -> None:
        steps = self._safe_int(self.entry_train_steps.get(), 20000, 1)
        batch_size = self._safe_int(self.entry_train_batch.get(), 8, 1)
        repo_id = self.entry_repo_id.get().strip()

        cmd = self.runner.build_train_command(
            repo_id=repo_id,
            steps=steps,
            batch_size=batch_size,
            use_amp=False,
            policy_type="act",
        )
        self.logger.info(f"Launching Local ACT Training: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot ACT Local Training")

    def _package_for_cloud(self) -> None:
        repo_id = self.entry_repo_id.get().strip()
        dataset_name = Path(repo_id).name
        dataset_path = self.root_dir / "datasets" / dataset_name
        if not dataset_path.exists():
            # Check root datasets
            alt_path = self.root_dir.parent / "datasets" / dataset_name
            if alt_path.exists():
                dataset_path = alt_path

        if not dataset_path.exists():
            self.logger.error(f"Cannot package: Dataset directory not found: {dataset_path}")
            self.status_label.configure(text="Dataset directory not found!", text_color="#ef4444")
            return

        try:
            zip_file = self.packager.package_dataset_to_zip(dataset_path)
            self.logger.info(f"Packaged dataset successfully: {zip_file}")
            self.status_label.configure(text=f"Packaged: {zip_file.name}", text_color="#22c55e")
        except Exception as e:
            self.logger.error(f"Failed to package dataset: {e}")
            self.status_label.configure(text=f"Package error: {e}", text_color="#ef4444")

    def _import_model_checkpoint(self) -> None:
        """Opens file dialog to import checkpoint archive or folder."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Policy Checkpoint (.zip)",
            filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
        )
        if not path:
            return

        ok, msg, imported_path = self.packager.import_policy(path)
        if ok:
            self.logger.info(f"Model imported successfully to {imported_path}")
            self.status_label.configure(text=f"Model Imported: {imported_path.name}", text_color="#22c55e")
            self._refresh_available_models()
        else:
            self.logger.error(f"Import failed: {msg}")
            self.status_label.configure(text=f"Import failed: {msg}", text_color="#ef4444")

    def _launch_rollout(self) -> None:
        selected = self.combo_model_select.get()
        if not selected or selected == "No Models Found":
            self.logger.error("No valid model checkpoint selected for rollout!")
            self.status_label.configure(text="Error: No model selected!", text_color="#ef4444")
            return

        # Extract path from mapping, fallback to manual entry
        policy_path = self._available_models_map.get(selected)
        if not policy_path:
            if "(" in selected and selected.endswith(")"):
                policy_path = selected.split("(")[-1][:-1].strip()
            else:
                policy_path = selected

        task = self.entry_rollout_task.get().strip()
        device = self.combo_device.get()
        top_camera = self._safe_int(self.combo_top_cam.get(), 0, 0)
        wrist_camera = self._safe_int(self.combo_wrist_cam.get(), 1, 0)
        interp = self._safe_int(self.entry_interp.get(), 2, 1)
        display_data = bool(self.switch_display_data_rollout.get())
        fps = self._safe_int(self.profile.get("fps", 30), 30, 1)

        cmd = self.runner.build_rollout_command(
            policy_path=policy_path,
            follower_port=self.combo_follower_port.get(),
            follower_id=self.entry_follower_id.get(),
            top_cam_idx=top_camera,
            wrist_cam_idx=wrist_camera,
            task=task,
            device=device,
            fps=fps,
            interpolation_multiplier=interp,
            display_data=display_data,
        )
        self.logger.info(f"Launching Autonomous Rollout: {' '.join(cmd)}")
        self.runner.run_command_in_terminal(cmd, window_title="LeRobot Autonomous Rollout")

    def _emergency_stop(self) -> None:
        count = self.runner.terminate_active_processes()
        self.logger.warning(f"EMERGENCY STOP executed. Terminated {count} process(es).")
        self.status_label.configure(text="EMERGENCY STOP ACTIVATED", text_color="#ef4444")

    def _open_datasets_dir(self) -> None:
        d = self.root_dir / "datasets"
        d.mkdir(parents=True, exist_ok=True)
        self._open_in_file_manager(d)

    def _open_exports_dir(self) -> None:
        d = self.root_dir / "exports"
        d.mkdir(parents=True, exist_ok=True)
        self._open_in_file_manager(d)

    def _open_models_dir(self) -> None:
        d = self.root_dir / "models"
        d.mkdir(parents=True, exist_ok=True)
        self._open_in_file_manager(d)

    def _open_in_file_manager(self, path: Path) -> None:
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(path)])
            else:
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            self.logger.warning(f"Could not open file manager for {path}: {e}")


def main():
    app = StudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
