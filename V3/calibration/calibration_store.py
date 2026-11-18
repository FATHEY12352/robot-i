"""Persistent per-arm, per-joint SO-101 tick calibration."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Dict, Optional

DEFAULT_CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
HOME_POSE_DEG = {1: 0.0, 2: -90.0, 3: 90.0, 4: 0.0, 5: 0.0, 6: 0.0}
TICKS_PER_REV = 4096
ZERO_TICKS = 2048
TICK_PER_DEG = TICKS_PER_REV / 360.0
_DEFAULT_ARM_CAL = {str(joint_id): {"min_ticks": 0, "max_ticks": 4095, "zero_ticks": ZERO_TICKS} for joint_id in range(1, 7)}
_DEFAULT_CALIBRATION = {"version": "3.0.0", "follower": deepcopy(_DEFAULT_ARM_CAL), "leader": deepcopy(_DEFAULT_ARM_CAL)}


def _normalise_joint(value: dict) -> dict:
    low = max(0, min(4095, int(value.get("min_ticks", 0))))
    high = max(0, min(4095, int(value.get("max_ticks", 4095))))
    zero = max(0, min(4095, int(value.get("zero_ticks", ZERO_TICKS))))
    return {"min_ticks": low, "max_ticks": high, "zero_ticks": zero}


class CalibrationStore:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_CALIBRATION_FILE
        self.data = deepcopy(_DEFAULT_CALIBRATION)
        if os.path.isfile(self.filepath):
            try:
                self.load()
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                self.data = deepcopy(_DEFAULT_CALIBRATION)

    def save(self) -> None:
        parent = os.path.dirname(os.path.abspath(self.filepath))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2, sort_keys=True)

    def load(self) -> None:
        with open(self.filepath, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("calibration root must be an object")
        for arm_id in ("follower", "leader"):
            arm_data = loaded.get(arm_id, {})
            if not isinstance(arm_data, dict):
                continue
            for joint_id in range(1, 7):
                key = str(joint_id)
                if key in arm_data and isinstance(arm_data[key], dict):
                    self.data[arm_id][key] = _normalise_joint({**self.data[arm_id][key], **arm_data[key]})
        if "version" in loaded:
            self.data["version"] = str(loaded["version"])

    def get_joint(self, arm_id: str, joint_id: int) -> dict:
        if arm_id not in ("follower", "leader"):
            raise KeyError(arm_id)
        if not 1 <= int(joint_id) <= 6:
            raise ValueError(f"invalid joint id: {joint_id}")
        return deepcopy(self.data[arm_id][str(joint_id)])

    def get_home_ticks(self, arm_id: str = "follower") -> Dict[int, int]:
        return {joint_id: self.validate_ticks(arm_id, joint_id, round(self.get_joint(arm_id, joint_id)["zero_ticks"] + angle * TICK_PER_DEG)) for joint_id, angle in HOME_POSE_DEG.items()}

    def set_joint_min(self, arm_id: str, joint_id: int, ticks: int) -> None:
        self._ensure_joint(arm_id, joint_id)
        self.data[arm_id][str(joint_id)]["min_ticks"] = max(0, min(4095, int(ticks)))

    def set_joint_max(self, arm_id: str, joint_id: int, ticks: int) -> None:
        self._ensure_joint(arm_id, joint_id)
        self.data[arm_id][str(joint_id)]["max_ticks"] = max(0, min(4095, int(ticks)))

    def set_joint_zero(self, arm_id: str, joint_id: int, ticks: int) -> None:
        self._ensure_joint(arm_id, joint_id)
        self.data[arm_id][str(joint_id)]["zero_ticks"] = max(0, min(4095, int(ticks)))

    def validate_ticks(self, arm_id: str, joint_id: int, ticks: int) -> int:
        joint = self.get_joint(arm_id, joint_id)
        low, high = sorted((joint["min_ticks"], joint["max_ticks"]))
        return max(low, min(high, max(0, min(4095, int(ticks)))))

    def _ensure_joint(self, arm_id: str, joint_id: int) -> None:
        if arm_id not in ("follower", "leader"):
            raise KeyError(arm_id)
        if not 1 <= int(joint_id) <= 6:
            raise ValueError(f"invalid joint id: {joint_id}")
        self.data.setdefault(arm_id, {}).setdefault(str(joint_id), deepcopy(_DEFAULT_ARM_CAL[str(joint_id)]))

    def reset_to_defaults(self, arm_id: Optional[str] = None) -> None:
        if arm_id is None:
            self.data["follower"] = deepcopy(_DEFAULT_ARM_CAL)
            self.data["leader"] = deepcopy(_DEFAULT_ARM_CAL)
        else:
            if arm_id not in ("follower", "leader"):
                raise KeyError(arm_id)
            self.data[arm_id] = deepcopy(_DEFAULT_ARM_CAL)

    def to_dict(self) -> dict:
        return deepcopy(self.data)
