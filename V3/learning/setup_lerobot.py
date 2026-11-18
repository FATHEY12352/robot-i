"""LeRobot environment checks and SO-101 configuration helpers."""

from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class LeRobotConfig:
    robot_type: str = "so101_follower"
    robot_port: str = "COM38"
    leader_port: str = "COM39"
    fps: int = 30
    cameras: Dict[str, int] = field(default_factory=dict)
    dataset_repo_id: str = "local/so101"
    num_episodes: int = 50

    def __post_init__(self) -> None:
        if self.fps <= 0 or self.num_episodes <= 0:
            raise ValueError("fps and num_episodes must be positive")
        if not self.robot_port or not self.leader_port:
            raise ValueError("robot and leader ports are required")

    def to_dict(self) -> dict:
        return asdict(self)


def check_lerobot() -> dict:
    """Return import availability and installed package version."""
    spec = importlib.util.find_spec("lerobot")
    result = {"installed": spec is not None, "version": None}
    if spec is not None:
        try:
            result["version"] = version("lerobot")
        except PackageNotFoundError:
            pass
    return result


def _yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "{}" if not value else "\n" + "\n".join(f"  {k}: {v}" for k, v in value.items())
    if isinstance(value, str):
        return value if value and all(ch.isalnum() or ch in "._/-" for ch in value) else repr(value)
    return str(value)


def write_sample_config(path: Optional[str] = None, config: Optional[LeRobotConfig] = None) -> str:
    """Write a dependency-free sample YAML configuration."""
    destination = Path(path) if path else Path(__file__).with_name("lerobot_config.yaml")
    cfg = config or LeRobotConfig()
    rows = [f"{key}: {_yaml_scalar(value)}" for key, value in cfg.to_dict().items()]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return str(destination)


if __name__ == "__main__":
    print(check_lerobot())
    print("Sample configuration:", write_sample_config())
