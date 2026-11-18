"""V3 kinematics package — SO-101 / SO-ARM100 Forward & Inverse Kinematics."""

from .so101_kinematics import (
    SO101Kinematics,
    JOINT_LIMITS_DEG,
    ZERO_TICKS,
    TICKS_PER_REV,
    DEG_PER_TICK,
    TICK_PER_DEG,
    forward_kinematics,
    inverse_kinematics,
    deg_to_ticks,
    ticks_to_deg,
    clamp_to_limits,
)

__all__ = [
    "SO101Kinematics",
    "JOINT_LIMITS_DEG",
    "ZERO_TICKS",
    "TICKS_PER_REV",
    "DEG_PER_TICK",
    "TICK_PER_DEG",
    "forward_kinematics",
    "inverse_kinematics",
    "deg_to_ticks",
    "ticks_to_deg",
    "clamp_to_limits",
]
