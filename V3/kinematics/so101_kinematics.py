"""SO-101 forward and inverse kinematics."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import least_squares

JOINT_LIMITS_DEG: Dict[int, Tuple[float, float]] = {
    1: (-150.0, 150.0),
    2: (-105.0, 105.0),
    3: (-95.0, 95.0),
    4: (-105.0, 105.0),
    5: (-90.0, 90.0),
    6: (0.0, 95.0),
}
HOME_POSE_DEG: Dict[int, float] = {1: 0.0, 2: -90.0, 3: 90.0, 4: 0.0, 5: 0.0, 6: 0.0}
TICKS_PER_REV = 4096
ZERO_TICKS = 2048
DEG_PER_TICK = 360.0 / TICKS_PER_REV
TICK_PER_DEG = TICKS_PER_REV / 360.0
_DH_PARAMS = ((0.0, 0.0, 90.0), (0.0, 117.0, 0.0), (0.0, 96.0, 0.0), (0.0, 0.0, 90.0), (85.0, 0.0, -90.0), (60.0, 0.0, 0.0))


def _dh_matrix(theta: float, d: float, a: float, alpha: float) -> np.ndarray:
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return np.array(((ct, -st * ca, st * sa, a * ct), (st, ct * ca, -ct * sa, a * st), (0.0, sa, ca, d), (0.0, 0.0, 0.0, 1.0)), dtype=float)


def _transform(angles_deg: List[float]) -> np.ndarray:
    if len(angles_deg) != 6:
        raise ValueError("expected six joint angles")
    transform = np.eye(4)
    for angle, (d, a, alpha) in zip(angles_deg, _DH_PARAMS):
        if not math.isfinite(float(angle)):
            raise ValueError("joint angles must be finite")
        transform = transform @ _dh_matrix(math.radians(float(angle)), d, a, math.radians(alpha))
    return transform


def _euler_zyx(rotation: np.ndarray) -> Tuple[float, float, float]:
    sy = math.hypot(float(rotation[0, 0]), float(rotation[1, 0]))
    if sy > 1e-9:
        roll = math.degrees(math.atan2(rotation[2, 1], rotation[2, 2]))
        pitch = math.degrees(math.atan2(-rotation[2, 0], sy))
        yaw = math.degrees(math.atan2(rotation[1, 0], rotation[0, 0]))
    else:
        roll = math.degrees(math.atan2(-rotation[1, 2], rotation[1, 1]))
        pitch = math.degrees(math.atan2(-rotation[2, 0], sy))
        yaw = 0.0
    return roll, pitch, yaw


def deg_to_ticks(degrees: float, joint_id: int) -> int:
    if joint_id not in JOINT_LIMITS_DEG:
        raise ValueError(f"invalid joint id: {joint_id}")
    if not math.isfinite(float(degrees)):
        raise ValueError("degrees must be finite")
    return max(0, min(TICKS_PER_REV - 1, int(round(ZERO_TICKS + float(degrees) * TICK_PER_DEG))))


def ticks_to_deg(ticks: int, joint_id: int) -> float:
    if joint_id not in JOINT_LIMITS_DEG:
        raise ValueError(f"invalid joint id: {joint_id}")
    if not 0 <= int(ticks) <= TICKS_PER_REV - 1:
        raise ValueError("ticks must be in the range 0..4095")
    return (int(ticks) - ZERO_TICKS) * DEG_PER_TICK


def clamp_to_limits(angles_deg: List[float]) -> List[float]:
    if len(angles_deg) != 6:
        raise ValueError("expected six joint angles")
    return [max(JOINT_LIMITS_DEG[i][0], min(JOINT_LIMITS_DEG[i][1], float(value))) for i, value in enumerate(angles_deg, 1)]


def forward_kinematics(joint_angles_deg: List[float]) -> Dict[str, float]:
    transform = _transform(joint_angles_deg)
    roll, pitch, yaw = _euler_zyx(transform[:3, :3])
    return {"x": float(transform[0, 3]), "y": float(transform[1, 3]), "z": float(transform[2, 3]), "roll": roll, "pitch": pitch, "yaw": yaw}


def inverse_kinematics(x: float, y: float, z: float, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, max_iter: int = 200, tol: float = 0.5, damping: float = 0.1, q_init: Optional[List[float]] = None) -> List[float]:
    target = np.asarray((x, y, z), dtype=float)
    if target.shape != (3,) or not np.isfinite(target).all():
        raise ValueError("target coordinates must be finite")
    initial = np.asarray(q_init if q_init is not None else [0.0] * 6, dtype=float)
    if initial.shape != (6,):
        raise ValueError("q_init must contain six angles")
    lower = np.array([JOINT_LIMITS_DEG[i][0] for i in range(1, 7)], dtype=float)
    upper = np.array([JOINT_LIMITS_DEG[i][1] for i in range(1, 7)], dtype=float)
    initial = np.clip(initial, lower, upper)

    def residual(angles: np.ndarray) -> np.ndarray:
        return (_transform(angles.tolist())[:3, 3] - target) / max(float(damping), 1e-3)

    result = least_squares(residual, initial, bounds=(lower, upper), max_nfev=max_iter, xtol=tol / 1000.0, ftol=tol / 1000.0, gtol=tol / 1000.0)
    error = float(np.linalg.norm(_transform(result.x.tolist())[:3, 3] - target))
    if error > max(50.0, tol * 10.0):
        raise ValueError(f"IK did not converge: final_error={error:.2f}mm")
    return [float(value) for value in result.x]


class SO101Kinematics:
    JOINT_LIMITS_DEG = JOINT_LIMITS_DEG
    ZERO_TICKS = ZERO_TICKS
    TICKS_PER_REV = TICKS_PER_REV

    def forward_kinematics(self, joint_angles_deg: List[float]) -> Dict[str, float]:
        return forward_kinematics(joint_angles_deg)

    def inverse_kinematics(self, x: float, y: float, z: float, roll: float = 0.0, pitch: float = 0.0, yaw: float = 0.0, q_init: Optional[List[float]] = None) -> List[float]:
        return inverse_kinematics(x, y, z, roll, pitch, yaw, q_init=q_init)

    def deg_to_ticks(self, degrees: float, joint_id: int) -> int:
        return deg_to_ticks(degrees, joint_id)

    def ticks_to_deg(self, ticks: int, joint_id: int) -> float:
        return ticks_to_deg(ticks, joint_id)

    def clamp_to_limits(self, angles_deg: List[float]) -> List[float]:
        return clamp_to_limits(angles_deg)

    def home_pose_ticks(self) -> Dict[int, int]:
        return {joint_id: deg_to_ticks(angle, joint_id) for joint_id, angle in HOME_POSE_DEG.items()}
