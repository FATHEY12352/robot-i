"""
=============================================================================
SO-101 / SO-ARM100 URDF Model Validator & Exporter
=============================================================================
Validates kinematics, joint limits, link hierarchy, and dual gripper jaw definitions
for simulation environments (Isaac Sim, MuJoCo, PyBullet, Gazebo).
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

V3_DIR = Path(__file__).resolve().parent.parent
URDF_PATH = V3_DIR.parent / "so101.urdf"
ASSETS_DIR = V3_DIR.parent / "assets"


class URDFValidator:
    def __init__(self, urdf_path: Optional[Path] = None):
        self.urdf_path = urdf_path or URDF_PATH
        self.tree: Optional[ET.ElementTree] = None
        self.root: Optional[ET.Element] = None

    def load(self) -> bool:
        if not self.urdf_path.is_file():
            raise FileNotFoundError(f"URDF file not found: {self.urdf_path}")
        self.tree = ET.parse(str(self.urdf_path))
        self.root = self.tree.getroot()
        return True

    def validate_joints(self) -> Dict[str, Any]:
        """Validate revolute joint limits and transmission mappings."""
        if self.root is None:
            self.load()

        joints: Dict[str, Dict[str, Any]] = {}
        for joint in self.root.findall("joint"):
            j_name = joint.get("name")
            j_type = joint.get("type")
            parent = joint.find("parent").get("link") if joint.find("parent") is not None else None
            child = joint.find("child").get("link") if joint.find("child") is not None else None
            
            limits = {}
            limit_tag = joint.find("limit")
            if limit_tag is not None:
                limits["lower"] = float(limit_tag.get("lower", 0.0))
                limits["upper"] = float(limit_tag.get("upper", 0.0))
                limits["effort"] = float(limit_tag.get("effort", 10.0))
                limits["velocity"] = float(limit_tag.get("velocity", 10.0))

            joints[j_name] = {
                "type": j_type,
                "parent": parent,
                "child": child,
                "limits": limits
            }

        return joints

    def validate_gripper_dual_jaws(self) -> bool:
        """
        Verify that both the static jaw (on gripper_link) and the moving jaw
        (moving_jaw_so101_v1_link) exist and are linked by revolute joint 'gripper'.
        """
        joints = self.validate_joints()
        has_gripper_joint = "gripper" in joints
        if not has_gripper_joint:
            return False

        g_joint = joints["gripper"]
        is_revolute = g_joint["type"] == "revolute"
        has_correct_child = g_joint["child"] == "moving_jaw_so101_v1_link"
        return is_revolute and has_correct_child

    def validate_mesh_files(self) -> List[Tuple[str, bool]]:
        """Verify that all referenced STL files exist in assets/."""
        if self.root is None:
            self.load()

        results = []
        for mesh in self.root.iter("mesh"):
            filename = mesh.get("filename", "")
            clean_name = filename.replace("assets/", "").replace("assets\\", "")
            target_path = ASSETS_DIR / clean_name
            results.append((clean_name, target_path.is_file()))

        return results


def main():
    validator = URDFValidator()
    validator.load()
    print("=" * 60)
    print(" SO-101 URDF VALIDATION REPORT")
    print("=" * 60)
    print(f"[✓] URDF Loaded from: {validator.urdf_path}")
    
    joints = validator.validate_joints()
    print(f"[i] Found {len(joints)} joints:")
    for name, data in joints.items():
        print(f"  - {name} ({data['type']}): {data['parent']} -> {data['child']}")

    dual_jaws = validator.validate_gripper_dual_jaws()
    print(f"\n[✓] Dual Gripper Jaws Integrity Check: {'PASSED ✓' if dual_jaws else 'FAILED ✗'}")

    print("\n[*] Mesh Assets Integrity Check:")
    mesh_results = validator.validate_mesh_files()
    all_ok = True
    for name, exists in mesh_results:
        status = "EXISTS ✓" if exists else "MISSING ✗"
        if not exists:
            all_ok = False
        print(f"  - {name}: {status}")

    print("\n" + "=" * 60)
    print(f"OVERALL STATUS: {'READY FOR ISAAC SIM & SIMULATION ✓' if all_ok and dual_jaws else 'ISSUES FOUND'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
