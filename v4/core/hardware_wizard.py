"""
Hardware Discovery and Calibration Scanner Wizard for SO-101 Robotics Studio V4.
Handles serial COM port discovery, OpenCV camera enumeration & preview, and LeRobot calibration lookup.
"""

from __future__ import annotations

import os
import platform
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .logger import get_logger

try:
    import serial.tools.list_ports
except ImportError:
    serial = None

try:
    import cv2
    try:
        cv2.setLogLevel(0)
    except Exception:
        pass
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image
except ImportError:
    Image = None


class HardwareWizard:
    """Provides hardware discovery services for serial bus arms and dual cameras."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        self.logger = get_logger("HardwareWizard")
        if root_dir is None:
            self.root_dir = Path(__file__).resolve().parents[1]
        else:
            self.root_dir = Path(root_dir)
        self._camera_lock = threading.Lock()

    # -------------------------------------------------------------------------
    # 1. Serial Port Discovery & Differential Scanning

    def list_serial_ports(self) -> List[Dict[str, str]]:
        """Scans and returns all available serial ports with description and hardware ID."""
        ports: List[Dict[str, str]] = []
        if serial is None:
            self.logger.warning("pyserial is not available; serial ports cannot be enumerated.")
            return ports

        try:
            for p in serial.tools.list_ports.comports():
                ports.append({
                    "port": p.device,
                    "description": p.description or p.device,
                    "hwid": p.hwid or "",
                    "manufacturer": getattr(p, "manufacturer", "") or "",
                })
        except Exception as e:
            self.logger.error(f"Error enumerating serial ports: {e}")

        return sorted(ports, key=lambda x: x["port"])

    def get_port_names(self) -> List[str]:
        """Convenience method returning just port identifiers (e.g. ['COM38', 'COM39'])."""
        return [p["port"] for p in self.list_serial_ports()]

    def take_port_snapshot(self) -> Set[str]:
        """Captures set of current port names for plug-and-play differential detection."""
        return set(self.get_port_names())

    def diff_ports(self, before_snapshot: Set[str]) -> Tuple[List[str], List[str]]:
        """Returns ([newly_added_ports], [removed_ports]) by comparing to prior snapshot."""
        current = set(self.get_port_names())
        added = sorted(list(current - before_snapshot))
        removed = sorted(list(before_snapshot - current))
        return added, removed

    def test_port_access(self, port: str, baudrate: int = 1000000, timeout: float = 0.2) -> bool:
        """Tests whether a serial port can be opened and accessed with the given baudrate."""
        if serial is None or not port:
            return False
        try:
            import serial as ser_mod
            with ser_mod.Serial(port=port, baudrate=baudrate, timeout=timeout) as s:
                return s.is_open
        except Exception as e:
            self.logger.debug(f"Failed to access port {port} at {baudrate} baud: {e}")
            return False

    def scan_feetech_servos(
        self,
        port: str,
        baudrate: int = 1000000,
        timeout: float = 0.03,
        expected_ids: Optional[List[int]] = None,
    ) -> Tuple[bool, List[int], str]:
        """
        Pings Feetech STS/SCS bus servos (IDs 1-6) on the specified port.
        Returns: (success_bool, alive_ids_list, human_readable_status_message)
        """
        if serial is None or not port:
            return False, [], "pyserial not available or port empty"

        if expected_ids is None:
            expected_ids = [1, 2, 3, 4, 5, 6]

        alive: List[int] = []
        volts: List[float] = []
        try:
            import serial as ser_mod
            with ser_mod.Serial(port=port, baudrate=baudrate, timeout=timeout) as s:
                for sid in range(1, 10):
                    chk = (~(sid + 2 + 1)) & 0xFF
                    packet = bytes([0xFF, 0xFF, sid, 2, 1, chk])
                    s.reset_input_buffer()
                    s.write(packet)
                    resp = s.read(6)
                    if len(resp) >= 6 and resp[0] == 0xFF and resp[1] == 0xFF and resp[2] == sid:
                        alive.append(sid)
                        # Read voltage register 62 (1 byte)
                        chk_read = (~(sid + 4 + 2 + 62 + 1)) & 0xFF
                        s.reset_input_buffer()
                        s.write(bytes([0xFF, 0xFF, sid, 4, 2, 62, 1, chk_read]))
                        r_read = s.read(7)
                        if len(r_read) >= 7 and r_read[0] == 0xFF and r_read[1] == 0xFF and r_read[2] == sid:
                            volts.append(r_read[5] / 10.0)
        except Exception as e:
            err_msg = str(e)
            if "Access is denied" in err_msg or "PermissionError" in err_msg:
                return False, [], f"Port {port} busy (Access Denied). Another process or terminal is holding it."
            return False, [], f"Could not access {port}: {err_msg}"

        avg_v = (sum(volts) / len(volts)) if volts else 0.0
        v_warning = ""
        if avg_v > 0.0 and avg_v < 8.5:
            v_warning = f" ⚠️ LOW VOLTAGE: {avg_v:.1f}V (USB phantom power). Connect 12V adapter!"
        elif avg_v >= 8.5:
            v_warning = f" (Voltage: {avg_v:.1f}V OK)"

        missing = [i for i in expected_ids if i not in alive]
        if not missing:
            msg = f"All {len(expected_ids)} Servos OK ({alive}){v_warning} - Ready!"
            return True, alive, msg
        elif alive:
            msg = f"Servos {alive} OK, but MISSING SERVO(S): {missing}!{v_warning} Check cable & 12V power."
            return False, alive, msg
        else:
            msg = f"No servos answered on {port} at {baudrate} baud. Verify arm 12V power switch."
            return False, [], msg

    # -------------------------------------------------------------------------
    # 2. Camera Discovery & Preview
    # -------------------------------------------------------------------------

    def scan_cameras(self, max_indices: int = 4) -> List[Dict[str, Any]]:
        """Probes video capture indices and returns available cameras with resolutions."""
        discovered: List[Dict[str, Any]] = []
        if cv2 is None:
            self.logger.warning("opencv-python is not available; cameras cannot be probed.")
            return discovered

        cv2.setNumThreads(1)
        for idx in range(max_indices):
            cap = None
            try:
                # Try generic backend first, fallback to DSHOW on Windows
                cap = cv2.VideoCapture(idx)
                if not cap.isOpened() and platform.system() == "Windows":
                    cap.release()
                    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)

                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    for _ in range(4):
                        cap.grab()
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = int(cap.get(cv2.CAP_PROP_FPS))
                        discovered.append({
                            "index": idx,
                            "width": w if w > 0 else 640,
                            "height": h if h > 0 else 480,
                            "fps": fps if fps > 0 else 30,
                            "is_working": True,
                        })
            except Exception as e:
                self.logger.debug(f"Exception probing camera index {idx}: {e}")
            finally:
                if cap is not None:
                    cap.release()

        return discovered

    def capture_preview_frame(
        self,
        camera_index: int,
        target_width: int = 320,
        target_height: int = 240,
        warmup_frames: int = 8,
        gamma: float = 1.0,
        open_timeout: float = 2.0,
    ) -> Optional[Any]:
        """Captures a test frame with bounded warmup, exposure correction, and RGB formatting."""
        if cv2 is None or Image is None:
            return None

        cap = None
        if not self._camera_lock.acquire(timeout=max(0.1, open_timeout)):
            self.logger.warning(f"Camera {camera_index} is busy with another preview request.")
            return None
        try:
            cv2.setNumThreads(1)
            try:
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY)
            except Exception:
                cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened() and platform.system() == "Windows":
                cap.release()
                cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

            if not cap.isOpened():
                return None

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Warmup reads are bounded in count; OpenCV owns backend read timing.
            for _ in range(max(0, min(warmup_frames, 12))):
                cap.grab()

            ret, frame = cap.read()
            if not ret or frame is None:
                return None

            # Optional tone-down / gamma correction if scene is overexposed
            if gamma != 1.0 and gamma > 0.1 and np is not None:
                inv_gamma = 1.0 / gamma
                table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                frame = cv2.LUT(frame, table)

            # Resize and convert BGR -> RGB
            resized = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        except Exception as e:
            self.logger.debug(f"Error capturing preview frame from camera {camera_index}: {e}")
            return None
        finally:
            if cap is not None:
                cap.release()
            self._camera_lock.release()

    # -------------------------------------------------------------------------
    # 3. LeRobot Calibration Profile Scanning
    # -------------------------------------------------------------------------

    def scan_calibration_profiles(self, custom_base_dir: Optional[Path | str] = None) -> Dict[str, List[str]]:
        """
        Scans LeRobot calibration directories for existing follower and leader arm configs.
        NOTE: 'so_follower' and 'so_leader' are the subfolder names used by LeRobot calibration store.
        """
        result = {
            "follower_ids": [],
            "leader_ids": [],
        }

        # Directories to search
        local_calib = self.root_dir / "calibration"
        user_home = Path.home()
        hf_cache_calib = user_home / ".cache" / "huggingface" / "lerobot" / "calibration"

        if custom_base_dir is not None:
            search_bases = [Path(custom_base_dir)]
        else:
            # Check local V4 calibration first, then user home cache
            search_bases = [local_calib, hf_cache_calib]

        for base in search_bases:
            if not base.exists():
                continue

            # Search recursively because LeRobot versions may add namespace or robot-id folders.
            for json_file in base.rglob("*.json"):
                try:
                    relative_parts = {part.lower() for part in json_file.relative_to(base).parts[:-1]}
                except ValueError:
                    continue
                if "so_follower" in relative_parts:
                    cid = json_file.stem
                    if cid not in result["follower_ids"]:
                        result["follower_ids"].append(cid)
                if "so_leader" in relative_parts:
                    cid = json_file.stem
                    if cid not in result["leader_ids"]:
                        result["leader_ids"].append(cid)

        result["follower_ids"].sort()
        result["leader_ids"].sort()
        return result

    def get_recommended_robot_ids(self, custom_base_dir: Optional[Path | str] = None) -> Tuple[str, str]:
        """Returns the best available (follower_id, leader_id), defaulting to standard defaults."""
        profiles = self.scan_calibration_profiles(custom_base_dir=custom_base_dir)
        follower_id = profiles["follower_ids"][0] if profiles["follower_ids"] else "my_follower"
        leader_id = profiles["leader_ids"][0] if profiles["leader_ids"] else "my_leader"
        return follower_id, leader_id
