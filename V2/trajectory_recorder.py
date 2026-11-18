"""
====================================================================
SO-100 / SO-101 Continuous Trajectory Recorder & Player
====================================================================
Lead-through kinesthetic teaching recorder:
- Records continuous raw motor positions at 25-30 Hz.
- Handles millions of points if needed.
- Replays recorded motions with precise timing, smooth startup, and looping.
"""

import os
import time
import json
import threading
from typing import List, Dict, Any, Optional
from so101_arm import SO101Arm

TRAJECTORIES_DIR = os.path.join(os.path.dirname(__file__), "trajectories")

class TrajectoryRecorder:
    def __init__(self, arm: SO101Arm):
        self.arm = arm
        self.is_recording = False
        self.is_playing = False
        self.frames: List[Dict[str, Any]] = []
        self.start_time = 0.0

        os.makedirs(TRAJECTORIES_DIR, exist_ok=True)

    def start_recording(self):
        """Start recording raw frames."""
        self.frames = []
        self.start_time = time.time()
        self.is_recording = True
        print("[*] Continuous trajectory recording STARTED...")

    def record_step(self, states: Dict[int, Dict]):
        """Record a single timestamped frame."""
        if not self.is_recording:
            return
        t = time.time() - self.start_time
        frame = {
            "t": round(t, 4),
            "raw": {sid: states[sid]["raw_pos"] for sid in range(1, 7) if sid in states}
        }
        self.frames.append(frame)

    def stop_recording(self, filename: Optional[str] = None) -> str:
        """Stop recording and save trajectory to disk."""
        self.is_recording = False
        if not filename:
            filename = f"motion_{time.strftime('%Y%m%d_%H%M%S')}.json"
        if not filename.endswith(".json"):
            filename += ".json"

        filepath = os.path.join(TRAJECTORIES_DIR, filename)
        meta = {
            "created_at": time.ctime(),
            "total_frames": len(self.frames),
            "duration_sec": self.frames[-1]["t"] if self.frames else 0.0,
            "frames": self.frames
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"[✓] Recording saved: {len(self.frames)} frames ({meta['duration_sec']:.2f}s) -> {filepath}")
        return filepath

    def list_saved_trajectories(self) -> List[str]:
        """List all saved trajectory files."""
        if not os.path.exists(TRAJECTORIES_DIR):
            return []
        files = [f for f in os.listdir(TRAJECTORIES_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        return files

    def load_trajectory(self, filename: str) -> List[Dict]:
        filepath = os.path.join(TRAJECTORIES_DIR, filename) if not os.path.isabs(filename) else filename
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("frames", [])

    def play(self, frames: List[Dict], loop: bool = False, speed_factor: float = 1.0, callback=None):
        """Play a trajectory smoothly."""
        if not frames:
            print("[!] No frames to play.")
            return

        self.is_playing = True
        self.arm.clear_all_overloads()
        self.arm.enable_all_torque()
        time.sleep(0.05)

        try:
            while self.is_playing:
                # Step 1: Smoothly move to the first frame of the trajectory using SYNC WRITE
                first_raw = {int(k): int(v) for k, v in frames[0]["raw"].items()}
                print("[*] Moving to start position of trajectory with SYNC WRITE...")
                self.arm.sync_write_raw(first_raw, speed=350)
                time.sleep(1.2) # Allow arm to reach start pose

                # Step 2: Stream trajectory frames using high-speed SYNC WRITE
                t_play_start = time.time()
                prev_goals = dict(first_raw)

                for i in range(len(frames)):
                    if not self.is_playing:
                        break

                    f = frames[i]
                    target_time = f["t"] / speed_factor
                    elapsed = time.time() - t_play_start

                    # Synchronize timing
                    if target_time > elapsed:
                        time.sleep(target_time - elapsed)

                    # Send all joint goals in ONE atomic 0.46ms packet!
                    raw_goals = {int(k): int(v) for k, v in f["raw"].items()}
                    safe_goals = {}

                    # Wrap-around & glitch filter: protect against 0/4096 sudden 360-degree reverse spins
                    for sid, val in raw_goals.items():
                        prev_val = prev_goals.get(sid, val)
                        delta = val - prev_val
                        # If a single 30ms step jumped by > 1500 ticks, it's a 0/4096 wrap seam!
                        if delta > 2000:
                            # e.g. 0 -> 4095: stay near 0
                            val = prev_val
                        elif delta < -2000:
                            # e.g. 4095 -> 0: stay near 4095
                            val = prev_val
                        safe_goals[sid] = val

                    prev_goals = safe_goals
                    self.arm.sync_write_raw(safe_goals, speed=850)

                    if callback:
                        callback(i, len(frames), safe_goals)

                if not loop:
                    break
                print("[*] Looping trajectory...")
                time.sleep(0.5)

        finally:
            self.is_playing = False
            print("[✓] Playback finished.")

    def stop_playback(self):
        self.is_playing = False

