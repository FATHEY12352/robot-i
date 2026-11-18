"""
====================================================================
SO-100 / SO-101 (SO-ARM100) Graphical Dashboard & Controller
====================================================================
Modern GUI controller for the 6-DOF arm using CustomTkinter.
Features:
- Individual joint sliders (Joints 1 to 6)
- Live feedback display (Angle, Voltage, Temperature)
- Preset poses (Home, Rest, Wave, Pick ready)
- Gripper control
- Free Drive mode (Move by hand, sliders update live)
- Motion recording & playback (Hand teaching)
"""

import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from so101_arm import SO101Arm

# Set visual theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SO101App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SO-101 / SO-ARM100 Robot Arm Dashboard")
        self.geometry("900 x 780")
        self.minsize(850, 720)

        # Robot interface
        self.arm = SO101Arm(port="COM38", baudrate=1000000)
        self.connected = False
        self.free_drive = False
        self.monitor_running = False

        # Slider variables & widgets
        self.sliders = {}
        self.val_labels = {}
        self.telemetry_labels = {}
        self.recorded_waypoints = []

        # Build UI layout
        self._build_top_bar()
        self._build_joints_panel()
        self._build_controls_panel()
        self._build_recorder_panel()

        # Connect automatically on startup
        self.after(300, self.connect_robot)

    def _build_top_bar(self):
        top_frame = ctk.CTkFrame(self, corner_radius=10)
        top_frame.pack(fill="x", padx=15, pady=(12, 6))

        title = ctk.CTkLabel(
            top_frame,
            text="SO-101 (SO-ARM100) 6-DOF Robotic Controller",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(side="left", padx=15, pady=10)

        self.status_badge = ctk.CTkLabel(
            top_frame,
            text="Disconnected",
            text_color="#ff5555",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_badge.pack(side="right", padx=15, pady=10)

        self.connect_btn = ctk.CTkButton(
            top_frame,
            text="Connect COM38",
            width=130,
            command=self.toggle_connection
        )
        self.connect_btn.pack(side="right", padx=10, pady=10)

        self.v_label = ctk.CTkLabel(top_frame, text="Supply: -- V", font=ctk.CTkFont(size=13))
        self.v_label.pack(side="right", padx=15, pady=10)

    def _build_joints_panel(self):
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.pack(fill="x", padx=15, pady=6)

        header = ctk.CTkLabel(
            main_frame,
            text="Joint Angle Control & Telemetry",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        header.pack(anchor="w", padx=15, pady=(8, 4))

        joint_names = {
            1: "J1: Shoulder Pan (Base Yaw)",
            2: "J2: Shoulder Lift (Pitch)",
            3: "J3: Elbow Flex (Pitch)",
            4: "J4: Wrist Flex (Pitch)",
            5: "J5: Wrist Roll",
            6: "J6: Gripper"
        }

        # Grid of sliders
        for sid in range(1, 7):
            row = ctk.CTkFrame(main_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=4)

            # Name label
            lbl = ctk.CTkLabel(row, text=joint_names[sid], width=200, anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
            lbl.pack(side="left", padx=5)

            # Slider
            slider = ctk.CTkSlider(
                row,
                from_=0.0,
                to=360.0,
                number_of_steps=720,
                width=340,
                command=lambda val, s=sid: self._on_slider_change(s, val)
            )
            slider.set(180.0)
            slider.pack(side="left", padx=10)
            self.sliders[sid] = slider

            # Value label
            v_lbl = ctk.CTkLabel(row, text="180.0°", width=65, font=ctk.CTkFont(size=13, family="Consolas"))
            v_lbl.pack(side="left", padx=5)
            self.val_labels[sid] = v_lbl

            # Telemetry label (temp / volt)
            t_lbl = ctk.CTkLabel(row, text="--°C", width=60, font=ctk.CTkFont(size=12), text_color="#aaaaaa")
            t_lbl.pack(side="left", padx=5)
            self.telemetry_labels[sid] = t_lbl

            # Quick jog buttons (+- 5 deg)
            minus_btn = ctk.CTkButton(
                row, text="-5°", width=40, height=26,
                command=lambda s=sid: self._jog_joint(s, -5.0)
            )
            minus_btn.pack(side="left", padx=3)

            plus_btn = ctk.CTkButton(
                row, text="+5°", width=40, height=26,
                command=lambda s=sid: self._jog_joint(s, +5.0)
            )
            plus_btn.pack(side="left", padx=3)

    def _build_controls_panel(self):
        ctrl_frame = ctk.CTkFrame(self, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=15, pady=6)

        # Title
        t_lbl = ctk.CTkLabel(ctrl_frame, text="Preset Poses & Quick Actions", font=ctk.CTkFont(size=15, weight="bold"))
        t_lbl.pack(anchor="w", padx=15, pady=(8, 4))

        btn_row1 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        btn_row1.pack(fill="x", padx=15, pady=4)

        # Preset pose buttons
        b_home = ctk.CTkButton(btn_row1, text="🏠 Home Pose", width=120, command=self.pose_home)
        b_home.pack(side="left", padx=5)

        b_rest = ctk.CTkButton(btn_row1, text="🛌 Rest Pose", width=120, fg_color="#445566", command=self.pose_rest)
        b_rest.pack(side="left", padx=5)

        b_wave = ctk.CTkButton(btn_row1, text="👋 Wave Demo", width=120, fg_color="#337755", command=self.pose_wave)
        b_wave.pack(side="left", padx=5)

        b_open_g = ctk.CTkButton(btn_row1, text="🟢 Open Gripper", width=120, fg_color="#2b8a3e", command=self.open_gripper)
        b_open_g.pack(side="left", padx=5)

        b_close_g = ctk.CTkButton(btn_row1, text="🔴 Close Gripper", width=120, fg_color="#c92a2a", command=self.close_gripper)
        b_close_g.pack(side="left", padx=5)

        # Row 2: Torque & Speed control
        btn_row2 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        btn_row2.pack(fill="x", padx=15, pady=6)

        self.torque_btn = ctk.CTkButton(
            btn_row2,
            text="🔓 Free Drive (Hand Move)",
            fg_color="#e67700",
            width=180,
            command=self.toggle_torque
        )
        self.torque_btn.pack(side="left", padx=5)

        spd_lbl = ctk.CTkLabel(btn_row2, text="Speed:", font=ctk.CTkFont(size=13))
        spd_lbl.pack(side="left", padx=(20, 5))

        self.speed_slider = ctk.CTkSlider(btn_row2, from_=100, to=1000, number_of_steps=9, width=160)
        self.speed_slider.set(400)
        self.speed_slider.pack(side="left", padx=5)

        self.speed_val = ctk.CTkLabel(btn_row2, text="400", width=40)
        self.speed_val.pack(side="left", padx=5)
        self.speed_slider.configure(command=lambda v: self.speed_val.configure(text=f"{int(v)}"))

    def _build_recorder_panel(self):
        rec_frame = ctk.CTkFrame(self, corner_radius=10)
        rec_frame.pack(fill="x", padx=15, pady=6)

        t_lbl = ctk.CTkLabel(rec_frame, text="Hand-Teaching & Motion Sequence Recorder", font=ctk.CTkFont(size=15, weight="bold"))
        t_lbl.pack(anchor="w", padx=15, pady=(8, 4))

        row = ctk.CTkFrame(rec_frame, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=4)

        b_rec = ctk.CTkButton(row, text="💾 Save Current Pose", width=150, command=self.record_current_pose)
        b_rec.pack(side="left", padx=5)

        b_play = ctk.CTkButton(row, text="▶ Play Sequence", width=140, fg_color="#1971c2", command=self.play_sequence)
        b_play.pack(side="left", padx=5)

        b_clear = ctk.CTkButton(row, text="🗑 Clear Waypoints", width=140, fg_color="#555555", command=self.clear_waypoints)
        b_clear.pack(side="left", padx=5)

        self.rec_status = ctk.CTkLabel(row, text="Waypoints saved: 0", font=ctk.CTkFont(size=13))
        self.rec_status.pack(side="left", padx=15)

    # -------------------------------------------------------------
    # Logic & Threading
    # -------------------------------------------------------------
    def connect_robot(self):
        if self.arm.connect():
            self.connected = True
            self.status_badge.configure(text="Connected (COM38)", text_color="#55ff55")
            self.connect_btn.configure(text="Disconnect")
            self._sync_sliders_with_robot()
            self._start_telemetry_loop()
        else:
            self.status_badge.configure(text="Failed to Connect", text_color="#ff5555")

    def toggle_connection(self):
        if self.connected:
            self.monitor_running = False
            self.arm.disconnect()
            self.connected = False
            self.status_badge.configure(text="Disconnected", text_color="#ff5555")
            self.connect_btn.configure(text="Connect COM38")
        else:
            self.connect_robot()

    def _sync_sliders_with_robot(self):
        states = self.arm.get_all_states()
        for sid, s in states.items():
            ang = s["angle"]
            if sid in self.sliders:
                self.sliders[sid].set(ang)
                self.val_labels[sid].configure(text=f"{ang:.1f}°")

    def _start_telemetry_loop(self):
        self.monitor_running = True
        t = threading.Thread(target=self._telemetry_worker, daemon=True)
        t.start()

    def _telemetry_worker(self):
        while self.monitor_running and self.connected:
            try:
                states = self.arm.get_all_states()
                if states:
                    # Update Voltage from Joint 1
                    if 1 in states:
                        v = states[1]["voltage"]
                        self.after(0, lambda val=v: self.v_label.configure(text=f"Supply: {val:.1f} V"))

                    # If Free Drive is enabled, update sliders live as user moves arm!
                    if self.free_drive:
                        for sid, s in states.items():
                            ang = s["angle"]
                            self.after(0, lambda s_id=sid, a=ang: self._update_slider_ui(s_id, a))

                    # Update temperature labels
                    for sid, s in states.items():
                        temp = s["temperature"]
                        self.after(0, lambda s_id=sid, t=temp: self.telemetry_labels[s_id].configure(text=f"{t}°C"))

            except Exception:
                pass
            time.sleep(0.12)

    def _update_slider_ui(self, sid, angle):
        if sid in self.sliders:
            self.sliders[sid].set(angle)
            self.val_labels[sid].configure(text=f"{angle:.1f}°")

    def _on_slider_change(self, sid, val):
        if self.free_drive:
            return # Don't send move commands during hand teaching
        angle = round(float(val), 1)
        self.val_labels[sid].configure(text=f"{angle:.1f}°")
        if self.connected:
            spd = int(self.speed_slider.get())
            self.arm.move_joint(sid, angle, speed=spd)

    def _jog_joint(self, sid, delta):
        cur = self.sliders[sid].get()
        target = max(0.0, min(360.0, cur + delta))
        self.sliders[sid].set(target)
        self._on_slider_change(sid, target)

    def toggle_torque(self):
        if not self.connected:
            return
        self.free_drive = not self.free_drive
        if self.free_drive:
            self.arm.disable_all_torque()
            self.torque_btn.configure(text="🔒 Lock Torque (Stop Free Drive)", fg_color="#2b8a3e")
        else:
            self.arm.enable_all_torque()
            self.torque_btn.configure(text="🔓 Free Drive (Hand Move)", fg_color="#e67700")

    def pose_home(self):
        """Centered safe home pose."""
        if not self.connected:
            return
        home_angles = {1: 180.0, 2: 180.0, 3: 180.0, 4: 180.0, 5: 180.0, 6: 90.0}
        self._execute_smooth_pose(home_angles)

    def pose_rest(self):
        """Folded rest pose."""
        if not self.connected:
            return
        rest_angles = {1: 180.0, 2: 90.0, 3: 270.0, 4: 180.0, 5: 180.0, 6: 45.0}
        self._execute_smooth_pose(rest_angles)

    def pose_wave(self):
        """Friendly waving sequence."""
        if not self.connected:
            return
        threading.Thread(target=self._wave_worker, daemon=True).start()

    def _wave_worker(self):
        # Move up
        self.arm.move_pose({1: 180, 2: 150, 3: 200, 4: 180, 5: 180, 6: 120}, speed=400, wait=1.2)
        # Wave left-right on Wrist Roll (J5)
        for _ in range(3):
            self.arm.move_joint(5, 220, speed=600)
            time.sleep(0.4)
            self.arm.move_joint(5, 140, speed=600)
            time.sleep(0.4)
        self.arm.move_joint(5, 180, speed=500)
        self._sync_sliders_with_robot()

    def open_gripper(self):
        if self.connected:
            self.arm.open_gripper()
            self.sliders[6].set(120.0)
            self.val_labels[6].configure(text="120.0°")

    def close_gripper(self):
        if self.connected:
            self.arm.close_gripper()
            self.sliders[6].set(45.0)
            self.val_labels[6].configure(text="45.0°")

    def _execute_smooth_pose(self, pose):
        spd = int(self.speed_slider.get())
        for sid, ang in pose.items():
            self.sliders[sid].set(ang)
            self.val_labels[sid].configure(text=f"{ang:.1f}°")
            self.arm.move_joint(sid, ang, speed=spd)

    # -------------------------------------------------------------
    # Hand-Teaching / Waypoints Recorder
    # -------------------------------------------------------------
    def record_current_pose(self):
        pose = {}
        for sid in range(1, 7):
            pose[sid] = round(self.sliders[sid].get(), 1)
        self.recorded_waypoints.append(pose)
        self.rec_status.configure(text=f"Waypoints saved: {len(self.recorded_waypoints)}")

    def clear_waypoints(self):
        self.recorded_waypoints.clear()
        self.rec_status.configure(text="Waypoints saved: 0")

    def play_sequence(self):
        if not self.recorded_waypoints or not self.connected:
            messagebox.showinfo("Info", "No waypoints saved to play!")
            return
        threading.Thread(target=self._play_worker, daemon=True).start()

    def _play_worker(self):
        spd = int(self.speed_slider.get())
        for idx, pose in enumerate(self.recorded_waypoints):
            self.rec_status.configure(text=f"Playing waypoint {idx+1}/{len(self.recorded_waypoints)}")
            for sid, ang in pose.items():
                self.after(0, lambda s=sid, a=ang: self._update_slider_ui(s, a))
                self.arm.move_joint(sid, ang, speed=spd)
            time.sleep(1.2)
        self.rec_status.configure(text=f"Playback done. Total: {len(self.recorded_waypoints)}")

if __name__ == "__main__":
    app = SO101App()
    app.mainloop()

