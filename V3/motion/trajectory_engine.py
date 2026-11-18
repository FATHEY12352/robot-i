"""
Trajectory Recording & Playback Engine for SO-101 / SO-ARM100.

Records joint positions from Leader arm (COM39) at a configurable sample rate
and plays them back to Follower arm (COM38) with smooth interpolation.

Trajectory directory: D:\\projekt\\ARM\\V2\\V3\\trajectories\\
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

TRAJECTORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trajectories"
)

# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

Frame = Dict[str, Any]
# Each frame: {"timestamp": float, "joint_ticks": {1: int, 2: int, ..., 6: int}}


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TrajectoryRecorder:
    """Background-thread trajectory recorder."""

    def __init__(self):
        self._frames: List[Frame] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._arm_controller = None
        self._sample_hz: float = 50.0
        self._t_start: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, arm_controller: Any, sample_hz: float = 50.0) -> None:
        """
        Start background recording from arm_controller at sample_hz.

        arm_controller must expose read_telemetry_batch() returning
        a dict {servo_id: {"raw_pos": int, ...}}.
        """
        if self.is_recording:
            return
        self._arm_controller = arm_controller
        self._sample_hz = max(1.0, float(sample_hz))
        self._frames = []
        self._stop_event.clear()
        self._t_start = time.perf_counter()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> List[Frame]:
        """Stop recording and return captured frames."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        with self._lock:
            return list(self._frames)

    def _record_loop(self) -> None:
        interval = 1.0 / self._sample_hz
        while not self._stop_event.is_set():
            loop_start = time.perf_counter()
            try:
                batch = self._arm_controller.read_telemetry_batch()
                ticks: Dict[int, int] = {}
                if hasattr(batch, "servos"):
                    items = batch.servos.items()
                elif hasattr(batch, "items"):
                    items = batch.items()
                else:
                    items = ()
                for sid, data in items:
                    if isinstance(data, dict):
                        ticks[int(sid)] = int(data.get("raw_pos", data.get("position", 2048)))
                    elif hasattr(data, "raw_pos"):
                        ticks[int(sid)] = int(data.raw_pos)
                frame: Frame = {
                    "timestamp": time.perf_counter() - self._t_start,
                    "joint_ticks": ticks,
                }
                with self._lock:
                    self._frames.append(frame)
            except Exception:
                pass  # Swallow transient errors; don't crash recorder

            elapsed = time.perf_counter() - loop_start
            sleep_for = interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)


# ---------------------------------------------------------------------------
# Module-level recorder singleton
# ---------------------------------------------------------------------------

_global_recorder = TrajectoryRecorder()


def record_start(arm_controller: Any, hz: float = 50.0) -> None:
    """Start background trajectory recording from arm_controller at hz."""
    _global_recorder.start(arm_controller, hz=hz)


def record_stop() -> List[Frame]:
    """Stop recording and return captured frame list."""
    return _global_recorder.stop()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_trajectory(frames: List[Frame], filename: str) -> str:
    """
    Save trajectory frames to a JSON file.

    Args:
        frames: List of frame dicts (timestamp + joint_ticks).
        filename: Base filename (without directory path is OK; will be placed
                  under TRAJECTORY_DIR if not an absolute path).

    Returns:
        Absolute path of the saved file.
    """
    if not filename or os.path.basename(filename) != filename and not os.path.isabs(filename):
        raise ValueError("filename must be a file name or absolute path")
    if not os.path.isabs(filename):
        filepath = os.path.join(TRAJECTORY_DIR, filename)
    else:
        filepath = os.path.abspath(filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if frames:
        duration = frames[-1]["timestamp"] - frames[0]["timestamp"]
        hz_actual = len(frames) / max(duration, 1e-6)
    else:
        duration = 0.0
        hz_actual = 0.0

    payload = {
        "version": "3.0.0",
        "metadata": {
            "arm_leader": "COM39",
            "arm_follower": "COM38",
            "sample_hz": hz_actual,
            "frame_count": len(frames),
            "duration_sec": duration,
        },
        "frames": frames,
    }

    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    return filepath


def load_trajectory(filename: str) -> List[Frame]:
    """
    Load trajectory frames from a JSON file.

    Args:
        filename: Absolute path or base filename under TRAJECTORY_DIR.

    Returns:
        List of frame dicts.
    """
    if not os.path.isabs(filename):
        if os.path.basename(filename) != filename:
            raise ValueError("filename must be a file name or absolute path")
        filepath = os.path.join(TRAJECTORY_DIR, filename)
    else:
        filepath = os.path.abspath(filename)

    with open(filepath, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    return payload.get("frames", [])


# ---------------------------------------------------------------------------
# Interpolation Helper
# ---------------------------------------------------------------------------

def _lerp_ticks(t0: int, t1: int, alpha: float) -> int:
    """Linear interpolation between two tick values, handling 0/4095 wrap."""
    # Detect wraparound: if delta > 2048 in either direction, go the short way
    delta = t1 - t0
    if delta > 2048:
        delta -= 4096
    elif delta < -2048:
        delta += 4096
    return max(0, min(4095, int(round(t0 + alpha * delta))))


def _interpolate_frame(
    frame_a: Frame, frame_b: Frame, t: float
) -> Dict[int, int]:
    """
    Linearly interpolate joint_ticks between frame_a and frame_b at time t.

    t must be in [frame_a["timestamp"], frame_b["timestamp"]].
    """
    t_a = frame_a["timestamp"]
    t_b = frame_b["timestamp"]
    dt = t_b - t_a
    alpha = (t - t_a) / dt if dt > 1e-9 else 1.0
    alpha = max(0.0, min(1.0, alpha))

    ticks_a: Dict[int, int] = frame_a.get("joint_ticks", {})
    ticks_b: Dict[int, int] = frame_b.get("joint_ticks", {})
    all_ids = set(ticks_a) | set(ticks_b)

    result: Dict[int, int] = {}
    for sid in sorted(all_ids):
        va = ticks_a.get(sid, 2048)
        vb = ticks_b.get(sid, va)
        result[sid] = _lerp_ticks(int(va), int(vb), alpha)
    return result


# ---------------------------------------------------------------------------
# Playback
# ---------------------------------------------------------------------------

class TrajectoryPlayer:
    """
    Plays a recorded trajectory to an arm controller.

    Usage::

        player = TrajectoryPlayer(frames, arm_controller, speed_factor=1.0)
        player.start()
        # … do other things …
        player.stop()
    """

    def __init__(
        self,
        frames: List[Frame],
        arm_controller: Any,
        speed_factor: float = 1.0,
        loop: bool = False,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self.frames = frames
        self.arm_controller = arm_controller
        self.speed_factor = max(0.01, float(speed_factor))
        self.loop = loop
        self.on_complete = on_complete

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start playback in a background thread."""
        if self.is_playing or not self.frames:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the playback thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._thread = None

    def _play_loop(self) -> None:
        while not self._stop_event.is_set():
            self._play_once()
            if not self.loop:
                break

        if self.on_complete is not None:
            try:
                self.on_complete()
            except Exception:
                pass

    def _play_once(self) -> None:
        """Play the trajectory once from start to end."""
        if len(self.frames) < 2:
            # Single frame: send it immediately
            if self.frames:
                ticks = dict(self.frames[0].get("joint_ticks", {}))
                self._send(ticks)
            return

        t_start_wall = time.perf_counter()
        t_traj_start = self.frames[0]["timestamp"]
        t_traj_end = self.frames[-1]["timestamp"]
        duration = (t_traj_end - t_traj_start) / self.speed_factor

        # Build a sorted frame index for binary search
        sorted_frames = sorted(self.frames, key=lambda f: f["timestamp"])

        frame_idx = 0

        while not self._stop_event.is_set():
            wall_now = time.perf_counter()
            t_elapsed = (wall_now - t_start_wall) * self.speed_factor
            t_traj = t_traj_start + t_elapsed

            if t_traj >= t_traj_end:
                # Send final frame and stop
                ticks = dict(sorted_frames[-1].get("joint_ticks", {}))
                self._send(ticks)
                break

            # Advance frame_idx to find bracketing frames
            while (
                frame_idx < len(sorted_frames) - 2
                and sorted_frames[frame_idx + 1]["timestamp"] <= t_traj
            ):
                frame_idx += 1

            fa = sorted_frames[frame_idx]
            fb = sorted_frames[frame_idx + 1]
            ticks = _interpolate_frame(fa, fb, t_traj)
            self._send(ticks)

            # Sleep until next frame boundary (target ~100 Hz)
            next_wall = t_start_wall + (t_traj - t_traj_start + 0.01) / self.speed_factor
            sleep_for = next_wall - time.perf_counter()
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _send(self, ticks: Dict[int, int]) -> None:
        """Send tick positions, excluding joints known to be offline."""
        try:
            if hasattr(self.arm_controller, "registry"):
                active = set(self.arm_controller.registry.active_ids)
                ticks = {int(sid): int(value) for sid, value in ticks.items() if int(sid) in active}
            if ticks and hasattr(self.arm_controller, "sync_write_positions"):
                self.arm_controller.sync_write_positions(ticks)
        except Exception:
            pass


def play_trajectory(
    frames: List[Frame],
    arm_controller: Any,
    speed_factor: float = 1.0,
    loop: bool = False,
    on_complete: Optional[Callable[[], None]] = None,
) -> TrajectoryPlayer:
    """
    Create and start a TrajectoryPlayer.

    Args:
        frames: Trajectory frames from load_trajectory() or record_stop().
        arm_controller: Arm controller exposing sync_write_positions().
        speed_factor: Playback speed multiplier (1.0 = real-time).
        loop: Whether to loop playback continuously.
        on_complete: Optional callback when playback finishes.

    Returns:
        Running TrajectoryPlayer instance.
    """
    player = TrajectoryPlayer(frames, arm_controller, speed_factor, loop, on_complete)
    player.start()
    return player


def list_trajectories() -> List[Dict[str, Any]]:
    """List all saved trajectory files in TRAJECTORY_DIR."""
    if not os.path.isdir(TRAJECTORY_DIR):
        return []
    result = []
    for f in sorted(os.listdir(TRAJECTORY_DIR)):
        if f.endswith(".json"):
            fp = os.path.join(TRAJECTORY_DIR, f)
            try:
                with open(fp, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                frames_cnt = len(data.get("frames", []))
                meta = data.get("metadata", {})
                name = meta.get("name", f[:-5])
                result.append({
                    "filename": f,
                    "name": name,
                    "frames": frames_cnt,
                    "path": fp
                })
            except Exception:
                result.append({"filename": f, "name": f[:-5], "frames": 0, "path": fp})
    return result

