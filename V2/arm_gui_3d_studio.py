"""
====================================================================
SO-100 / SO-101 3D Robotic Studio & Kinesthetic Teaching Suite
====================================================================
Comprehensive Python application combining:
1. Real-time 3D Digital Twin visualization of the SO-100 robot arm
2. Joint calibration system (Min / Max raw limits & Gripper open/close)
3. Continuous trajectory recording & replay (Lead-through hand teaching)
4. Manual joint sliders and preset robotic poses
"""

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

import numpy as np

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

from so101_arm import SO101Arm
from so101_kinematics import SO101Kinematics
from calibration_manager import CalibrationManager
from trajectory_recorder import TrajectoryRecorder

# Dark modern theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SO101StudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SO-101 (SO-ARM100) 3D Studio & Lead-Through Teaching")
        self.geometry("1300 x 850")
        self.minsize(1200, 780)

        # Core Robot & Modules
        self.arm = SO101Arm(port="COM38", baudrate=1000000)
        self.calib = CalibrationManager()
        self.recorder = TrajectoryRecorder(self.arm)

        self.connected = False
        self.free_drive = False
        self.loop_running = False

        # Live telemetry cache
        self.current_angles = {1: 180.0, 2: 180.0, 3: 180.0, 4: 180.0, 5: 180.0, 6: 60.0}
        self.current_raws = {1: 2048, 2: 2048, 3: 2048, 4: 2048, 5: 2048, 6: 1200}
        self.voltage = 0.0

        # UI Widgets storage
        self.sliders = {}
        self.slider_labels = {}
        self.calib_labels = {}
        self.calib_bars = {}

        # Build Layout
        self._build_top_bar()
        self._build_main_layout()

        # Connect automatically after UI draws
        self.after(300, self.connect_robot)

    # -------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------
    def _build_top_bar(self):
        top = ctk.CTkFrame(self, corner_radius=10)
        top.pack(fill="x", padx=15, pady=(10, 5))

        title = ctk.CTkLabel(
            top,
            text="SO-101 3D DIGITAL TWIN & LEAD-THROUGH TEACHING STUDIO",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.pack(side="left", padx=15, pady=8)

        self.status_badge = ctk.CTkLabel(
            top,
            text="Disconnected",
            text_color="#ff5555",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_badge.pack(side="right", padx=15, pady=8)

        self.conn_btn = ctk.CTkButton(
            top, text="Connect COM38", width=120, command=self.toggle_connection
        )
        self.conn_btn.pack(side="right", padx=10, pady=8)

        self.v_label = ctk.CTkLabel(top, text="Supply: -- V", font=ctk.CTkFont(size=13))
        self.v_label.pack(side="right", padx=15, pady=8)

    def _build_main_layout(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15, pady=5)

        # Left Column: 3D Visualization Canvas
        left_frame = ctk.CTkFrame(content, corner_radius=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=5)
        self._build_3d_panel(left_frame)

        # Right Column: Tabview with Controls
        right_frame = ctk.CTkFrame(content, corner_radius=10, width=540)
        right_frame.pack(side="right", fill="both", padx=(8, 0), pady=5)
        self._build_tabs_panel(right_frame)

    def _build_3d_panel(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 0))

        title = ctk.CTkLabel(
            header,
            text="Real-Time 3D Arm Digital Twin",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.pack(side="left", padx=5)

        self.ee_coords_lbl = ctk.CTkLabel(
            header,
            text="End-Effector: X=0 Y=0 Z=0 mm",
            font=ctk.CTkFont(size=12, family="Consolas"),
            text_color="#3399ff"
        )
        self.ee_coords_lbl.pack(side="right", padx=5)

        # Matplotlib 3D Figure
        self.fig = plt.Figure(figsize=(5.5, 5.5), facecolor='#1e1e1e')
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_facecolor('#1e1e1e')

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        # 3D View Angle Controls below canvas
        view_ctrls = ctk.CTkFrame(parent, fg_color="transparent")
        view_ctrls.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(view_ctrls, text="Azimuth:").pack(side="left", padx=5)
        self.azim_slider = ctk.CTkSlider(view_ctrls, from_=0, to=360, width=130, command=self._on_view_change)
        self.azim_slider.set(45)
        self.azim_slider.pack(side="left", padx=5)

        ctk.CTkLabel(view_ctrls, text="Elevation:").pack(side="left", padx=5)
        self.elev_slider = ctk.CTkSlider(view_ctrls, from_=-20, to=90, width=130, command=self._on_view_change)
        self.elev_slider.set(25)
        self.elev_slider.pack(side="left", padx=5)

        reset_btn = ctk.CTkButton(view_ctrls, text="Reset View", width=80, command=self._reset_3d_view)
        reset_btn.pack(side="right", padx=5)

        self._draw_3d_arm(self.current_angles)

    def _build_tabs_panel(self, parent):
        self.tabview = ctk.CTkTabview(parent)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        # Three main tabs
        self.tab_record = self.tabview.add("🔴 Motion Recording")
        self.tab_calib = self.tabview.add("🎯 Calibration (Min/Max)")
        self.tab_manual = self.tabview.add("🎛 Manual Jog & Poses")

        self._build_recording_tab(self.tab_record)
        self._build_calibration_tab(self.tab_calib)
        self._build_manual_tab(self.tab_manual)

    # -------------------------------------------------------------
    # Tab 1: Continuous Trajectory Recording & Replay
    # -------------------------------------------------------------
    def _build_recording_tab(self, parent):
        desc = ctk.CTkLabel(
            parent,
            text="Lead-Through Teaching: Move the arm by hand to demonstrate,\nrecord continuous raw steps, and replay identically.",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa",
            justify="center"
        )
        desc.pack(padx=10, pady=(5, 10))

        # Torque Button (Free Drive)
        self.torque_toggle_btn = ctk.CTkButton(
            parent,
            text="🔓 Enable Free Drive (Torque OFF - Move by Hand)",
            fg_color="#e67700",
            hover_color="#d9480f",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_free_drive
        )
        self.torque_toggle_btn.pack(fill="x", padx=15, pady=6)

        # Recording Section Frame
        rec_box = ctk.CTkFrame(parent, corner_radius=8)
        rec_box.pack(fill="x", padx=15, pady=10)

        r_title = ctk.CTkLabel(rec_box, text="Continuous Trajectory Recorder", font=ctk.CTkFont(size=14, weight="bold"))
        r_title.pack(anchor="w", padx=15, pady=(8, 4))

        self.rec_btn = ctk.CTkButton(
            rec_box,
            text="🔴 Start Recording Motion",
            fg_color="#c92a2a",
            hover_color="#a61e4d",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_recording
        )
        self.rec_btn.pack(fill="x", padx=15, pady=8)

        self.rec_counter_lbl = ctk.CTkLabel(
            rec_box,
            text="Status: Ready (0 frames recorded)",
            font=ctk.CTkFont(size=13, family="Consolas"),
            text_color="#40c057"
        )
        self.rec_counter_lbl.pack(padx=15, pady=(0, 8))

        # Playback Section Frame
        play_box = ctk.CTkFrame(parent, corner_radius=8)
        play_box.pack(fill="x", padx=15, pady=10)

        p_title = ctk.CTkLabel(play_box, text="Execution & Replay Engine", font=ctk.CTkFont(size=14, weight="bold"))
        p_title.pack(anchor="w", padx=15, pady=(8, 4))

        # Trajectory file selector
        f_row = ctk.CTkFrame(play_box, fg_color="transparent")
        f_row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_row, text="Trajectory File:").pack(side="left", padx=5)

        self.traj_dropdown = ctk.CTkComboBox(f_row, values=["Last Recorded Session"], width=240)
        self.traj_dropdown.pack(side="left", padx=5)
        self._refresh_trajectory_list()

        refresh_btn = ctk.CTkButton(f_row, text="🔄", width=36, command=self._refresh_trajectory_list)
        refresh_btn.pack(side="left", padx=5)

        # Options
        opt_row = ctk.CTkFrame(play_box, fg_color="transparent")
        opt_row.pack(fill="x", padx=15, pady=4)

        self.loop_checkbox = ctk.CTkCheckBox(opt_row, text="🔁 Loop Playback Continuously")
        self.loop_checkbox.pack(side="left", padx=5)

        ctk.CTkLabel(opt_row, text="Speed:").pack(side="left", padx=(15, 5))
        self.play_speed_combo = ctk.CTkComboBox(opt_row, values=["0.5x", "1.0x (Normal)", "1.5x", "2.0x"], width=110)
        self.play_speed_combo.set("1.0x (Normal)")
        self.play_speed_combo.pack(side="left", padx=5)

        self.play_btn = ctk.CTkButton(
            play_box,
            text="▶ Replay Motion on Robot",
            fg_color="#1864ab",
            hover_color="#1971c2",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle_playback
        )
        self.play_btn.pack(fill="x", padx=15, pady=10)

    # -------------------------------------------------------------
    # Tab 2: Calibration (Min / Max Raw Limits)
    # -------------------------------------------------------------
    def _build_calibration_tab(self, parent):
        desc = ctk.CTkLabel(
            parent,
            text="Calibration: Move each joint to its mechanical limits (Min & Max)\nand capture the raw encoder values (e.g. Gripper open/closed).",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa",
            justify="center"
        )
        desc.pack(padx=10, pady=(5, 10))

        joint_names = {
            1: "J1: Base Pan",
            2: "J2: Shoulder Lift",
            3: "J3: Elbow Flex",
            4: "J4: Wrist Flex",
            5: "J5: Wrist Roll",
            6: "J6: Gripper"
        }

        # Grid of calibration rows
        for sid in range(1, 7):
            row = ctk.CTkFrame(parent, corner_radius=6)
            row.pack(fill="x", padx=10, pady=4)

            # Name
            lbl = ctk.CTkLabel(row, text=joint_names[sid], width=110, anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
            lbl.pack(side="left", padx=5)

            # Min capture button
            btn_min = ctk.CTkButton(
                row, text="Set MIN", width=68, height=26, fg_color="#343a40",
                command=lambda s=sid: self._capture_limit(s, is_min=True)
            )
            btn_min.pack(side="left", padx=3)

            # Progress bar showing % between min and max
            bar = ctk.CTkProgressBar(row, width=110, height=12)
            bar.set(0.5)
            bar.pack(side="left", padx=6)
            self.calib_bars[sid] = bar

            # Max capture button
            btn_max = ctk.CTkButton(
                row, text="Set MAX", width=68, height=26, fg_color="#343a40",
                command=lambda s=sid: self._capture_limit(s, is_min=False)
            )
            btn_max.pack(side="left", padx=3)

            # Limits readout
            lim_text = f"Min:{self.calib.data[str(sid)]['raw_min']} | Max:{self.calib.data[str(sid)]['raw_max']}"
            t_lbl = ctk.CTkLabel(row, text=lim_text, width=130, font=ctk.CTkFont(size=11, family="Consolas"))
            t_lbl.pack(side="left", padx=5)
            self.calib_labels[sid] = t_lbl

        # Save Button
        save_btn = ctk.CTkButton(
            parent,
            text="💾 Save Calibration to calibration.json",
            fg_color="#2b8a3e",
            hover_color="#2f9e44",
            height=34,
            command=self._save_calibration
        )
        save_btn.pack(fill="x", padx=15, pady=(15, 5))

    # -------------------------------------------------------------
    # Tab 3: Manual Jogging & Poses
    # -------------------------------------------------------------
    def _build_manual_tab(self, parent):
        joint_names = {
            1: "J1: Base Pan",
            2: "J2: Shoulder Lift",
            3: "J3: Elbow Flex",
            4: "J4: Wrist Flex",
            5: "J5: Wrist Roll",
            6: "J6: Gripper"
        }

        for sid in range(1, 7):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)

            ctk.CTkLabel(row, text=joint_names[sid], width=110, anchor="w", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)

            slider = ctk.CTkSlider(
                row, from_=0.0, to=360.0, width=220,
                command=lambda val, s=sid: self._on_manual_slider(s, val)
            )
            slider.set(180.0)
            slider.pack(side="left", padx=5)
            self.sliders[sid] = slider

            v_lbl = ctk.CTkLabel(row, text="180.0°", width=60, font=ctk.CTkFont(size=12, family="Consolas"))
            v_lbl.pack(side="left", padx=5)
            self.slider_labels[sid] = v_lbl

        # Preset pose buttons
        p_frame = ctk.CTkFrame(parent, fg_color="transparent")
        p_frame.pack(fill="x", padx=10, pady=10)

        b_home = ctk.CTkButton(p_frame, text="🏠 Home", width=95, command=self._pose_home)
        b_home.pack(side="left", padx=4)

        b_rest = ctk.CTkButton(p_frame, text="🛌 Rest", width=95, fg_color="#445566", command=self._pose_rest)
        b_rest.pack(side="left", padx=4)

        b_wave = ctk.CTkButton(p_frame, text="👋 Wave", width=95, fg_color="#337755", command=self._pose_wave)
        b_wave.pack(side="left", padx=4)

        b_open = ctk.CTkButton(p_frame, text="🟢 Open", width=95, fg_color="#2b8a3e", command=self.arm.open_gripper)
        b_open.pack(side="left", padx=4)

        b_close = ctk.CTkButton(p_frame, text="🔴 Close", width=95, fg_color="#c92a2a", command=self.arm.close_gripper)
        b_close.pack(side="left", padx=4)

    # -------------------------------------------------------------
    # 3D Arm Drawing Engine (Forward Kinematics)
    # -------------------------------------------------------------
    def _draw_3d_arm(self, angles):
        fk = SO101Kinematics.compute_fk(angles)
        self.ax.cla()

        # Extract points
        pts = np.array([
            fk["p0_base"],
            fk["p1_shoulder_pan"],
            fk["p2_shoulder_lift"],
            fk["p3_elbow"],
            fk["p4_wrist_flex"],
            fk["p5_wrist_roll"],
            fk["p6_ee"]
        ])

        # Plot Robot Skeleton Links (Thick cyan/orange lines)
        self.ax.plot(pts[:, 0], pts[:, 1], pts[:, 2], '-o', color='#ff922b', linewidth=5, markersize=8, markerfacecolor='#22b8cf', markeredgecolor='white')

        # Draw Gripper Fingers (V-shape opening)
        p6 = fk["p6_ee"]
        fl = fk["finger_left"]
        fr = fk["finger_right"]
        self.ax.plot([p6[0], fl[0]], [p6[1], fl[1]], [p6[2], fl[2]], color='#51cf66', linewidth=4)
        self.ax.plot([p6[0], fr[0]], [p6[1], fr[1]], [p6[2], fr[2]], color='#51cf66', linewidth=4)

        # Draw Base Circular Stand
        theta = np.linspace(0, 2*np.pi, 25)
        r = 60.0
        self.ax.plot(r*np.cos(theta), r*np.sin(theta), np.zeros_like(theta), color='#868e96', linewidth=2)

        # Plot Ground Grid
        for g in np.linspace(-250, 250, 6):
            self.ax.plot([-250, 250], [g, g], [0, 0], color='#2c2c2c', linewidth=0.8)
            self.ax.plot([g, g], [-250, 250], [0, 0], color='#2c2c2c', linewidth=0.8)

        # 3D Axis styling
        self.ax.set_xlim([-300, 300])
        self.ax.set_ylim([-300, 300])
        self.ax.set_zlim([0, 400])

        self.ax.set_xlabel("X (mm)", color='#aaaaaa', fontsize=9)
        self.ax.set_ylabel("Y (mm)", color='#aaaaaa', fontsize=9)
        self.ax.set_zlabel("Z (mm)", color='#aaaaaa', fontsize=9)

        self.ax.tick_params(colors='#777777', labelsize=8)
        self.ax.grid(False)

        # Set viewpoint
        azim = self.azim_slider.get()
        elev = self.elev_slider.get()
        self.ax.view_init(elev=elev, azim=azim)

        self.canvas.draw_idle()

        # Update end-effector label
        ee = fk["p6_ee"]
        self.ee_coords_lbl.configure(text=f"EE: X={ee[0]:.0f} Y={ee[1]:.0f} Z={ee[2]:.0f} mm (Grip: {fk['gripper_opening_mm']}mm)")

    def _on_view_change(self, _=None):
        self._draw_3d_arm(self.current_angles)

    def _reset_3d_view(self):
        self.azim_slider.set(45)
        self.elev_slider.set(25)
        self._draw_3d_arm(self.current_angles)

    # -------------------------------------------------------------
    # Robot Communication & Background Telemetry Thread
    # -------------------------------------------------------------
    def connect_robot(self):
        if self.arm.connect():
            self.connected = True
            self.status_badge.configure(text="Connected (COM38)", text_color="#51cf66")
            self.conn_btn.configure(text="Disconnect")
            self._start_telemetry_loop()
        else:
            self.status_badge.configure(text="Failed to Connect", text_color="#ff5555")

    def toggle_connection(self):
        if self.connected:
            self.loop_running = False
            self.arm.disconnect()
            self.connected = False
            self.status_badge.configure(text="Disconnected", text_color="#ff5555")
            self.conn_btn.configure(text="Connect COM38")
        else:
            self.connect_robot()

    def _start_telemetry_loop(self):
        self.loop_running = True
        threading.Thread(target=self._telemetry_worker, daemon=True).start()

    def _telemetry_worker(self):
        frame_count = 0
        while self.loop_running and self.connected:
            if self.recorder.is_playing:
                # Pause serial bus telemetry reading during playback so playback has 100% bandwidth!
                time.sleep(0.04)
                continue

            try:
                states = self.arm.get_all_states()
                if states and len(states) >= 4:
                    frame_count += 1
                    # Record frame if continuous recording is active!
                    if self.recorder.is_recording:
                        self.recorder.record_step(states)
                        n_frames = len(self.recorder.frames)
                        t_sec = self.recorder.frames[-1]["t"] if self.recorder.frames else 0.0
                        self.after(0, lambda n=n_frames, t=t_sec: self.rec_counter_lbl.configure(text=f"🔴 Recording: {n} frames ({t:.1f}s)"))

                    # Update raw and angle cache
                    for sid, s in states.items():
                        self.current_angles[sid] = s["angle"]
                        self.current_raws[sid] = s["raw_pos"]

                    # Update 3D render at ~15-20 FPS
                    if frame_count % 2 == 0:
                        self.after(0, lambda a=dict(self.current_angles): self._draw_3d_arm(a))

                    # Update UI telemetry
                    if 1 in states:
                        v = states[1]["voltage"]
                        self.after(0, lambda val=v: self.v_label.configure(text=f"Supply: {val:.1f} V"))

                    # If Free Drive is active, update manual sliders
                    if self.free_drive:
                        for sid, s in states.items():
                            ang = s["angle"]
                            self.after(0, lambda s_id=sid, a=ang: self._sync_slider(s_id, a))

                    # Update calibration progress bars
                    for sid, s in states.items():
                        pct = self.calib.raw_to_percent(sid, s["raw_pos"]) / 100.0
                        self.after(0, lambda s_id=sid, p=pct: self.calib_bars[s_id].set(p))

            except Exception:
                pass
            time.sleep(0.033) # ~30 Hz polling rate

    def _sync_slider(self, sid, angle):
        if sid in self.sliders:
            self.sliders[sid].set(angle)
            self.slider_labels[sid].configure(text=f"{angle:.1f}°")

    # -------------------------------------------------------------
    # Calibration Controls
    # -------------------------------------------------------------
    def _capture_limit(self, joint_id: int, is_min: bool):
        raw = self.current_raws.get(joint_id, 2048)
        if is_min:
            self.calib.set_min(joint_id, raw)
            print(f"[Calibration] Joint {joint_id} MIN set to {raw}")
        else:
            self.calib.set_max(joint_id, raw)
            print(f"[Calibration] Joint {joint_id} MAX set to {raw}")

        r_min = self.calib.data[str(joint_id)]["raw_min"]
        r_max = self.calib.data[str(joint_id)]["raw_max"]
        self.calib_labels[joint_id].configure(text=f"Min:{r_min} | Max:{r_max}")

    def _save_calibration(self):
        self.calib.save()
        messagebox.showinfo("Calibration Saved", "All joint limits successfully saved to calibration.json!")

    # -------------------------------------------------------------
    # Continuous Trajectory Actions
    # -------------------------------------------------------------
    def toggle_free_drive(self):
        if not self.connected:
            return
        self.free_drive = not self.free_drive
        if self.free_drive:
            self.arm.disable_all_torque()
            self.torque_toggle_btn.configure(text="🔒 Lock Torque (Stop Free Drive)", fg_color="#2b8a3e")
        else:
            self.arm.enable_all_torque()
            self.torque_toggle_btn.configure(text="🔓 Enable Free Drive (Torque OFF - Move by Hand)", fg_color="#e67700")

    def toggle_recording(self):
        if not self.recorder.is_recording:
            # Start
            self.recorder.start_recording()
            self.rec_btn.configure(text="⏹ Stop Recording Motion", fg_color="#343a40")
        else:
            # Stop
            saved_path = self.recorder.stop_recording()
            self.rec_btn.configure(text="🔴 Start Recording Motion", fg_color="#c92a2a")
            self.rec_counter_lbl.configure(text=f"Saved: {len(self.recorder.frames)} frames ({os.path.basename(saved_path)})")
            self._refresh_trajectory_list()

    def _refresh_trajectory_list(self):
        files = self.recorder.list_saved_trajectories()
        vals = ["Last Recorded Session"] + files
        self.traj_dropdown.configure(values=vals)
        if vals:
            self.traj_dropdown.set(vals[0])

    def toggle_playback(self):
        if self.recorder.is_playing:
            self.recorder.stop_playback()
            self.play_btn.configure(text="▶ Replay Motion on Robot", fg_color="#1864ab")
            return

        if hasattr(self, "_starting_play") and self._starting_play:
            return
        self._starting_play = True

        choice = self.traj_dropdown.get()
        if choice == "Last Recorded Session":
            frames = self.recorder.frames
        else:
            frames = self.recorder.load_trajectory(choice)

        if not frames:
            messagebox.showwarning("Warning", "No motion frames found to replay!")
            self._starting_play = False
            return

        loop = self.loop_checkbox.get()
        spd_str = self.play_speed_combo.get().split("x")[0]
        try:
            speed_factor = float(spd_str)
        except Exception:
            speed_factor = 1.0

        self.play_btn.configure(text="⏹ Stop Replay", fg_color="#c92a2a")

        def playback_cb(idx, total, raw_dict):
            angles = {}
            for sid_s, r in raw_dict.items():
                sid = int(sid_s)
                ang = r * (360.0 / 4096.0)
                angles[sid] = ang
                self.current_angles[sid] = ang
                self.current_raws[sid] = r
            if idx % 2 == 0:
                self.after(0, lambda a=dict(angles): self._draw_3d_arm(a))

        def run():
            try:
                self.recorder.play(frames, loop=loop, speed_factor=speed_factor, callback=playback_cb)
            finally:
                self._starting_play = False
                self.after(0, lambda: self.play_btn.configure(text="▶ Replay Motion on Robot", fg_color="#1864ab"))

        threading.Thread(target=run, daemon=True).start()

    # -------------------------------------------------------------
    # Manual Controls & Poses
    # -------------------------------------------------------------
    def _on_manual_slider(self, sid, val):
        if self.free_drive:
            return
        angle = round(float(val), 1)
        self.slider_labels[sid].configure(text=f"{angle:.1f}°")
        self.current_angles[sid] = angle
        if self.connected:
            self.arm.move_joint(sid, angle, speed=400)
        self._draw_3d_arm(self.current_angles)

    def _pose_home(self):
        pose = {1: 180.0, 2: 180.0, 3: 180.0, 4: 180.0, 5: 180.0, 6: 90.0}
        self.arm.smooth_move_pose(pose, duration=1.2)
        for sid, a in pose.items():
            self._sync_slider(sid, a)

    def _pose_rest(self):
        pose = {1: 180.0, 2: 90.0, 3: 270.0, 4: 180.0, 5: 180.0, 6: 45.0}
        self.arm.smooth_move_pose(pose, duration=1.2)
        for sid, a in pose.items():
            self._sync_slider(sid, a)

    def _pose_wave(self):
        threading.Thread(target=self._wave_worker, daemon=True).start()

    def _wave_worker(self):
        self.arm.smooth_move_pose({1: 180, 2: 150, 3: 200, 4: 180, 5: 180, 6: 120}, duration=1.2)
        for _ in range(3):
            self.arm.move_joint(5, 220, speed=600)
            time.sleep(0.35)
            self.arm.move_joint(5, 140, speed=600)
            time.sleep(0.35)
        self.arm.move_joint(5, 180, speed=400)

if __name__ == "__main__":
    app = SO101StudioApp()
    app.mainloop()

