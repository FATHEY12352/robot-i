"""
====================================================================
SO-100 / SO-101 Calibration Manager (Min / Max Raw Limits)
====================================================================
Stores, loads, and maps raw encoder limits (0..4095) for all 6 joints.
Allows normalizing joint positions into percentages (0% - 100%)
and physical calibrated ranges.
"""

import json
import os
from typing import Dict, Any, Optional, Tuple

CALIBRATION_FILE = os.path.join(os.path.dirname(__file__), "calibration.json")

# Default SO-100 Raw Encoder Limits (Safety boundaries)
DEFAULT_CALIBRATION = {
    "1": {"name": "Shoulder Pan (Base)", "raw_min": 1000, "raw_max": 3100, "center": 2048, "desc": "Min=Right, Max=Left"},
    "2": {"name": "Shoulder Lift",        "raw_min": 900,  "raw_max": 3100, "center": 2048, "desc": "Min=Forward, Max=Backward"},
    "3": {"name": "Elbow Flex",           "raw_min": 800,  "raw_max": 3300, "center": 2048, "desc": "Min=Bent, Max=Extended"},
    "4": {"name": "Wrist Flex",           "raw_min": 600,  "raw_max": 3400, "center": 2048, "desc": "Min=Down, Max=Up"},
    "5": {"name": "Wrist Roll",           "raw_min": 500,  "raw_max": 3600, "center": 2048, "desc": "Min=CW, Max=CCW"},
    "6": {"name": "Gripper",              "raw_min": 650,  "raw_max": 1900, "center": 1200, "desc": "Min=Fully Closed, Max=Fully Open"},
}

class CalibrationManager:
    def __init__(self, filepath: str = CALIBRATION_FILE):
        self.filepath = filepath
        self.data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                return
            except Exception as e:
                print(f"[!] Error loading {self.filepath}: {e}")
        # Initialize defaults
        self.data = json.loads(json.dumps(DEFAULT_CALIBRATION))
        self.save()

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
            print(f"[✓] Calibration saved to {self.filepath}")
        except Exception as e:
            print(f"[!] Error saving calibration: {e}")

    def set_min(self, joint_id: int, raw_value: int):
        sid = str(joint_id)
        if sid in self.data:
            self.data[sid]["raw_min"] = int(raw_value)
            self.save()

    def set_max(self, joint_id: int, raw_value: int):
        sid = str(joint_id)
        if sid in self.data:
            self.data[sid]["raw_max"] = int(raw_value)
            self.save()

    def get_limits(self, joint_id: int) -> Tuple[int, int]:
        sid = str(joint_id)
        if sid in self.data:
            return self.data[sid]["raw_min"], self.data[sid]["raw_max"]
        return 0, 4095

    def raw_to_percent(self, joint_id: int, raw_val: int) -> float:
        """Convert raw tick to 0.0% - 100.0% based on calibrated limits."""
        sid = str(joint_id)
        if sid not in self.data:
            return 50.0
        r_min = self.data[sid]["raw_min"]
        r_max = self.data[sid]["raw_max"]
        if r_max == r_min:
            return 50.0
        pct = (raw_val - r_min) / float(r_max - r_min) * 100.0
        return max(0.0, min(100.0, pct))

    def percent_to_raw(self, joint_id: int, pct: float) -> int:
        """Convert 0.0% - 100.0% back to raw motor ticks."""
        sid = str(joint_id)
        if sid not in self.data:
            return 2048
        r_min = self.data[sid]["raw_min"]
        r_max = self.data[sid]["raw_max"]
        raw = r_min + (pct / 100.0) * (r_max - r_min)
        return int(max(0, min(4095, round(raw))))

