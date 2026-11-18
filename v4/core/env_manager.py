"""
Environment and Hardware Acceleration Manager for SO-101 Robotics Studio V4.
Handles OS, Python venv, CUDA, GPU, and LeRobot dependency discovery and installation.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logger import get_logger


class EnvManager:
    """Manages Python virtual environments, hardware accelerators, and LeRobot toolchains."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        self.logger = get_logger("EnvManager")
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parents[1]
        else:
            self.root_dir = Path(root_dir)

        self.venv_dir = self.root_dir / ".venv"

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    @property
    def is_linux(self) -> bool:
        return platform.system() == "Linux"

    @property
    def is_raspberry_pi(self) -> bool:
        if not self.is_linux:
            return False
        machine = platform.machine().lower()
        if "arm" in machine or "aarch64" in machine:
            return True
        # Check /proc/device-tree/model
        model_path = Path("/proc/device-tree/model")
        if model_path.exists():
            try:
                content = model_path.read_text(encoding="utf-8", errors="ignore").lower()
                return "raspberry" in content
            except Exception:
                pass
        return False

    def get_venv_python(self) -> Path:
        """Returns the path to the virtual environment's Python executable."""
        if self.is_windows:
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"

    def get_venv_pip(self) -> Path:
        """Returns the path to the virtual environment's pip executable."""
        if self.is_windows:
            return self.venv_dir / "Scripts" / "pip.exe"
        return self.venv_dir / "bin" / "pip"

    def get_effective_python(self) -> str:
        """Returns the venv python if present, or sys.executable as fallback."""
        venv_py = self.get_venv_python()
        if venv_py.exists():
            return str(venv_py)
        return sys.executable

    def is_venv_active_or_present(self) -> bool:
        return self.get_venv_python().exists()

    def check_cuda_and_gpu(self) -> Dict[str, Any]:
        """Detects NVIDIA GPU, CUDA availability, VRAM, and TF32 compatibility."""
        result: Dict[str, Any] = {
            "cuda_available": False,
            "device_count": 0,
            "device_name": "None",
            "vram_gb": 0.0,
            "tf32_supported": False,
            "cuda_version": "N/A",
            "recommended_device": "cpu",
        }

        # Check via torch if importable
        try:
            import torch
            if torch.cuda.is_available():
                result["cuda_available"] = True
                result["device_count"] = torch.cuda.device_count()
                result["device_name"] = torch.cuda.get_device_name(0)
                mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                result["vram_gb"] = round(mem, 2)
                result["cuda_version"] = torch.version.cuda or "N/A"
                result["recommended_device"] = "cuda"

                # TF32 is supported on Ampere and newer architectures (compute capability >= 8.0)
                major, _ = torch.cuda.get_device_capability(0)
                result["tf32_supported"] = major >= 8
                return result
        except Exception as e:
            self.logger.debug(f"Direct torch CUDA query failed: {e}")

        # Fallback query via nvidia-smi if torch failed or not CUDA-enabled
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                proc = subprocess.run(
                    [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    parts = proc.stdout.strip().split("\n")[0].split(",")
                    name = parts[0].strip()
                    mem_mb = float(parts[1].strip()) if len(parts) > 1 else 0.0
                    result["device_name"] = name
                    result["vram_gb"] = round(mem_mb / 1024, 2)
                    result["device_count"] = len(proc.stdout.strip().split("\n"))
                    result["cuda_available"] = True
                    result["recommended_device"] = "cuda"
                    # RTX 30xx/40xx/50xx support TF32
                    if any(arch in name for arch in ["RTX 30", "RTX 40", "RTX 50", "A100", "H100"]):
                        result["tf32_supported"] = True
            except Exception as e:
                self.logger.debug(f"nvidia-smi fallback query failed: {e}")

        return result

    def check_lerobot_installed(self) -> Dict[str, Any]:
        """Checks if LeRobot package and its CLI tools are available."""
        result = {
            "installed": False,
            "version": "N/A",
            "cli_record": False,
            "cli_rollout": False,
            "cli_train": False,
            "cli_calibrate": False,
        }

        # Check binaries in PATH or venv Scripts/bin
        venv_dir_bin = self.venv_dir / ("Scripts" if self.is_windows else "bin")
        for tool in ["record", "rollout", "train", "calibrate"]:
            cmd_name = f"lerobot-{tool}"
            found = False
            # Check venv first
            if self.is_windows:
                candidate = venv_dir_bin / f"{cmd_name}.exe"
                if candidate.exists():
                    found = True
            else:
                candidate = venv_dir_bin / cmd_name
                if candidate.exists():
                    found = True

            # Check system PATH
            if not found and shutil.which(cmd_name):
                found = True

            result[f"cli_{tool}"] = found

        # Check Python module importability
        try:
            import lerobot
            result["installed"] = True
            result["version"] = getattr(lerobot, "__version__", ">=0.7.0")
        except ImportError:
            # Try running python in venv to check
            py_bin = self.get_effective_python()
            try:
                proc = subprocess.run(
                    [py_bin, "-c", "import lerobot; print(getattr(lerobot, '__version__', 'detected'))"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0:
                    result["installed"] = True
                    result["version"] = proc.stdout.strip()
            except Exception:
                pass

        return result

    def get_env_summary(self) -> Dict[str, Any]:
        """Aggregates system status into a single comprehensive dictionary."""
        gpu_info = self.check_cuda_and_gpu()
        lerobot_info = self.check_lerobot_installed()
        venv_py = self.get_venv_python()

        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "arch": platform.machine(),
            "is_raspberry_pi": self.is_raspberry_pi,
            "python_executable": str(venv_py) if venv_py.exists() else sys.executable,
            "python_version": platform.python_version(),
            "venv_exists": venv_py.exists(),
            "gpu": gpu_info,
            "lerobot": lerobot_info,
        }

    def generate_install_command_list(self) -> List[str]:
        """Generates list of shell commands to fully install PyTorch & LeRobot for this system."""
        py = self.get_effective_python()
        commands = [
            f'"{py}" -m pip install --upgrade pip setuptools wheel',
            f'"{py}" -m pip install -r "{self.root_dir / "requirements_gui.txt"}"',
        ]

        if self.is_windows or (self.is_linux and not self.is_raspberry_pi):
            # Install PyTorch with CUDA
            commands.append(
                f'"{py}" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124'
            )
        else:
            # Raspberry Pi / CPU Linux
            commands.append(f'"{py}" -m pip install torch torchvision')

        commands.append(f'"{py}" -m pip install lerobot>=0.7.0')
        return commands
