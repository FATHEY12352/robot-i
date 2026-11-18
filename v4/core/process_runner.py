"""
Process Runner and CLI Lifecycle Manager for SO-101 Robotics Studio V4.
Enforces LeRobot CLI standards, robot/teleop type invariants, and manages subprocess execution.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .logger import get_logger


class ProcessRunner:
    """Builds and launches LeRobot CLI commands in terminals or managed background threads."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        self.logger = get_logger("ProcessRunner")
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parents[1]
        else:
            self.root_dir = Path(root_dir)

        self.venv_dir = self.root_dir / ".venv"
        self._active_processes: List[subprocess.Popen] = []
        self._proc_lock = threading.Lock()

    def get_python_exe(self) -> str:
        """Returns isolated .venv python if present, else sys.executable."""
        if platform.system() == "Windows":
            candidate = self.venv_dir / "Scripts" / "python.exe"
        else:
            candidate = self.venv_dir / "bin" / "python"
        if candidate.exists():
            return str(candidate)
        return sys.executable

    def get_cli_bin(self, tool_name: str) -> str:
        """
        Locates the CLI tool (e.g. lerobot-record), preferring the local .venv,
        then active environment PATH, then fallback to tool name.
        """
        bin_dir = self.venv_dir / ("Scripts" if platform.system() == "Windows" else "bin")
        exe_ext = ".exe" if platform.system() == "Windows" else ""
        candidate = bin_dir / f"{tool_name}{exe_ext}"
        if candidate.exists():
            return str(candidate)

        # Check system/user environment PATH via shutil.which
        resolved = shutil.which(tool_name)
        if resolved:
            return resolved

        return tool_name

    def format_cameras_json(
        self,
        top_idx: int = 0,
        wrist_idx: int = 1,
        width: int = 640,
        height: int = 480,
        fps: int = 30
    ) -> str:
        """Builds JSON camera string matching LeRobot draccus schema."""
        cams = {
            "top": {
                "type": "opencv",
                "index_or_path": int(top_idx),
                "width": int(width),
                "height": int(height),
                "fps": int(fps)
            },
            "wrist": {
                "type": "opencv",
                "index_or_path": int(wrist_idx),
                "width": int(width),
                "height": int(height),
                "fps": int(fps)
            }
        }
        # Dump as compact JSON without unnecessary whitespace
        return json.dumps(cams, separators=(",", ":"))

    # -------------------------------------------------------------------------
    # 1. Calibrate Command Builder (MANDATORY FIX 2)
    # -------------------------------------------------------------------------

    def build_calibrate_command(
        self,
        mode: str = "follower",
        port: str = "COM38",
        robot_id: str = "my_follower"
    ) -> List[str]:
        """
        Builds lerobot-calibrate command.
        MANDATORY FIX 2: ALWAYS pass --robot.type=so101_follower or --teleop.type=so101_leader.
        """
        cmd_bin = self.get_cli_bin("lerobot-calibrate")
        cmd: List[str] = [cmd_bin]

        if mode.lower() in ["follower", "robot"]:
            cmd.extend([
                "--robot.type=so101_follower",
                f"--robot.port={port}",
                f"--robot.id={robot_id}",
            ])
        else:
            cmd.extend([
                "--teleop.type=so101_leader",
                f"--teleop.port={port}",
                f"--teleop.id={robot_id}",
            ])

        return cmd

    # -------------------------------------------------------------------------
    # 2. Record Command Builder (MANDATORY FIX 2 & 3)
    # -------------------------------------------------------------------------

    def build_record_command(
        self,
        follower_port: str = "COM38",
        leader_port: str = "COM39",
        follower_id: str = "my_follower",
        leader_id: str = "my_leader",
        top_cam_idx: int = 0,
        wrist_cam_idx: int = 1,
        repo_id: str = "voidstore/so101_pick_place",
        single_task: str = "Pick the target object and place it into the container",
        dataset_root: Optional[Path | str] = None,
        num_episodes: int = 50,
        fps: int = 30,
        push_to_hub: bool = False,
        display_data: bool = False,
        resume: bool = False,
    ) -> List[str]:
        """
        Builds lerobot-record command.
        MANDATORY FIX 2: --robot.type=so101_follower and --teleop.type=so101_leader.
        MANDATORY FIX 3: includes --dataset.single_task="..." and --dataset.push_to_hub=false by default.
        """
        cmd_bin = self.get_cli_bin("lerobot-record")
        if dataset_root is None:
            dataset_root = self.root_dir / "datasets" / Path(repo_id).name
        else:
            dataset_root = Path(dataset_root)

        cams_json = self.format_cameras_json(
            top_idx=top_cam_idx,
            wrist_idx=wrist_cam_idx,
            width=640,
            height=480,
            fps=fps
        )

        cmd: List[str] = [
            cmd_bin,
            "--robot.type=so101_follower",
            f"--robot.port={follower_port}",
            f"--robot.id={follower_id}",
            f"--robot.cameras={cams_json}",
            "--teleop.type=so101_leader",
            f"--teleop.port={leader_port}",
            f"--teleop.id={leader_id}",
            f"--dataset.fps={fps}",
            f"--dataset.repo_id={repo_id}",
            f"--dataset.single_task={single_task}",
            f"--dataset.root={Path(dataset_root).as_posix()}",
            f"--dataset.num_episodes={num_episodes}",
            f"--dataset.push_to_hub={'true' if push_to_hub else 'false'}",
            f"--display_data={'true' if display_data else 'false'}",
        ]

        if resume:
            cmd.append("--resume=true")

        return cmd

    # -------------------------------------------------------------------------
    # 2b. Teleoperate Command Builder (MANDATORY FIX 2)
    # -------------------------------------------------------------------------

    def build_teleoperate_command(
        self,
        follower_port: str = "COM38",
        leader_port: str = "COM39",
        follower_id: str = "my_follower",
        leader_id: str = "my_leader",
        fps: int = 60,
        display_data: bool = False,
    ) -> List[str]:
        """
        Builds lerobot-teleoperate command for live follower-leader arm control.
        MANDATORY FIX 2: ALWAYS pass --robot.type=so101_follower and --teleop.type=so101_leader.
        """
        cmd_bin = self.get_cli_bin("lerobot-teleoperate")
        cmd: List[str] = [
            cmd_bin,
            "--robot.type=so101_follower",
            f"--robot.port={follower_port}",
            f"--robot.id={follower_id}",
            "--teleop.type=so101_leader",
            f"--teleop.port={leader_port}",
            f"--teleop.id={leader_id}",
            f"--fps={fps}",
            f"--display_data={'true' if display_data else 'false'}",
        ]
        return cmd

    # -------------------------------------------------------------------------
    # 3. Train Command Builder (TF32 Enabled, AMP Disabled for ACT)
    # -------------------------------------------------------------------------

    def build_train_command(
        self,
        dataset_root: Optional[Path | str] = None,
        repo_id: str = "voidstore/so101_pick_place",
        output_dir: Optional[Path | str] = None,
        batch_size: int = 8,
        steps: int = 20000,
        save_freq: int = 5000,
        log_freq: int = 100,
        policy_type: str = "act",
        use_amp: bool = False,
        resume: bool = False,
    ) -> List[str]:
        """
        Builds ACT policy training command using train_act_wrapper.py to guarantee TF32 precision
        and disable AMP to prevent NaN loss explosions.
        """
        py_bin = self.get_python_exe()
        wrapper_path = self.root_dir / "core" / "train_act_wrapper.py"

        if dataset_root is None:
            dataset_root = self.root_dir / "datasets" / Path(repo_id).name
        else:
            dataset_root = Path(dataset_root)

        if output_dir is None:
            output_dir = self.root_dir / "outputs" / "train" / f"{policy_type}_{Path(repo_id).name}"
        else:
            output_dir = Path(output_dir)

        cmd: List[str] = [
            py_bin,
            str(wrapper_path),
            f"--dataset.repo_id={repo_id}",
            f"--dataset.root={Path(dataset_root).as_posix()}",
            f"--policy.type={policy_type}",
            f"--policy.push_to_hub=false",
            f"--output_dir={Path(output_dir).as_posix()}",
            f"--job_name={policy_type}_{Path(repo_id).name}",
            f"--batch_size={batch_size}",
            f"--steps={steps}",
            f"--save_freq={save_freq}",
            f"--log_freq={log_freq}",
            "--save_checkpoint=true",
            "--save_checkpoint_to_hub=false",
            f"--trackio.enable=false",
            # ACT stability invariant: AMP is always disabled, regardless of caller input.
            "--policy.use_amp=false",
            "--tf32=true",
        ]

        if resume:
            cmd.append("--resume=true")

        return cmd

    # -------------------------------------------------------------------------
    # 4. Rollout Command Builder (MANDATORY FIX 2 & 3)
    # -------------------------------------------------------------------------

    def build_rollout_command(
        self,
        policy_path: Path | str,
        follower_port: str = "COM38",
        follower_id: str = "my_follower",
        top_cam_idx: int = 0,
        wrist_cam_idx: int = 1,
        task: str = "Pick the target object and place it into the container",
        device: str = "cuda",
        fps: int = 30,
        interpolation_multiplier: int = 2,
        display_data: bool = False,
    ) -> List[str]:
        """
        Builds lerobot-rollout command for autonomous deployment.
        MANDATORY FIX 2: --robot.type=so101_follower
        MANDATORY FIX 3: full robot & camera args (--robot.type=so101_follower --robot.port=...
                         --robot.id=... --robot.cameras=... --fps=30 --task="...").
        CRITICAL ARCHITECTURE RULES:
          - NEVER pass --policy.type=act when --policy.path is given!
          - Include --strategy.type=base
          - Top-level --device=cuda or cpu
          - Include --interpolation_multiplier=2
        """
        cmd_bin = self.get_cli_bin("lerobot-rollout")
        policy_path_obj = Path(policy_path)

        cams_json = self.format_cameras_json(
            top_idx=top_cam_idx,
            wrist_idx=wrist_cam_idx,
            width=640,
            height=480,
            fps=fps
        )

        cmd: List[str] = [
            cmd_bin,
            "--robot.type=so101_follower",
            f"--robot.port={follower_port}",
            f"--robot.id={follower_id}",
            f"--robot.cameras={cams_json}",
            f"--fps={fps}",
            f"--task={task}",
            f"--policy.path={policy_path_obj.as_posix()}",
            "--strategy.type=base",
            f"--device={device}",
            f"--interpolation_multiplier={interpolation_multiplier}",
            f"--display_data={'true' if display_data else 'false'}",
        ]

        return cmd

    # -------------------------------------------------------------------------
    # 5. Process Execution & Management
    # -------------------------------------------------------------------------

    def run_command_in_terminal(self, cmd_args: List[str], window_title: str = "SO-101 Studio V4") -> subprocess.Popen:
        """
        Launches command in a standalone terminal window for interactive terminal display.
        On Windows: launches with CREATE_NEW_CONSOLE and cmd.exe /k to keep process tracked.
        On Linux: launches x-terminal-emulator or bash.
        """
        self.logger.info(f"Launching in terminal: {' '.join(cmd_args)}")

        if platform.system() == "Windows":
            cmd_line = subprocess.list2cmdline(cmd_args)
            win_args = ["cmd.exe", "/k", f"title {window_title} && {cmd_line}"]
            proc = subprocess.Popen(win_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
            with self._proc_lock:
                self._active_processes.append(proc)
            return proc
        else:
            # Linux fallback
            terms = ["x-terminal-emulator", "gnome-terminal", "konsole", "xterm"]
            for t in terms:
                if shutil.which(t):
                    proc = subprocess.Popen([t, "-e", "bash", "-lc", f"{shlex.join(cmd_args)}; exec bash"])
                    with self._proc_lock:
                        self._active_processes.append(proc)
                    return proc

            # Fallback to background process
            proc = subprocess.Popen(cmd_args)
            with self._proc_lock:
                self._active_processes.append(proc)
            return proc

    def run_command_async(
        self,
        cmd_args: List[str],
        on_output: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int], None]] = None
    ) -> subprocess.Popen:
        """
        Runs command asynchronously, streaming stdout and stderr line-by-line via callback.
        """
        self.logger.info(f"Running async process: {' '.join(cmd_args)}")

        proc = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        with self._proc_lock:
            self._active_processes.append(proc)

        def _reader_thread():
            try:
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        stripped = line.rstrip()
                        if stripped and on_output:
                            on_output(stripped)
                    proc.stdout.close()
                proc.wait()
            except Exception as e:
                self.logger.error(f"Process reader thread error: {e}")
            finally:
                with self._proc_lock:
                    if proc in self._active_processes:
                        self._active_processes.remove(proc)
                if on_finished:
                    on_finished(proc.returncode if proc.returncode is not None else -1)

        t = threading.Thread(target=_reader_thread, daemon=True)
        t.start()
        return proc

    def terminate_active_processes(self) -> int:
        """Emergency stop: terminates all spawned active processes and process trees."""
        count = 0
        with self._proc_lock:
            for p in list(self._active_processes):
                try:
                    if platform.system() == "Windows":
                        # Terminate entire process tree on Windows
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                            capture_output=True,
                            timeout=3
                        )
                    else:
                        p.terminate()
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Error terminating process {getattr(p, 'pid', 'unknown')}: {e}")
            self._active_processes.clear()

        self.logger.warning(f"Terminated {count} active studio processes.")
        return count
