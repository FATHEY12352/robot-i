"""
=============================================================================
NVIDIA Isaac Sim (Omniverse) SO-101 Robotic Arm Importer & Bridge
=============================================================================
Script executed inside NVIDIA Isaac Sim Python environment to import the
SO-101 URDF into the USD stage, configure PhysX articulation roots, and
stream live joints from V3 Studio or LeRobot.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

V3_DIR = Path(__file__).resolve().parent.parent
URDF_PATH = V3_DIR.parent / "so101.urdf"


def import_so101_to_isaac_sim(urdf_path: str = str(URDF_PATH), dest_usd_path: str = "so101.usd"):
    """
    Import SO-101 into Isaac Sim. Run with:
    isaac-sim.bat --python D:\\projekt\\ARM\\V2\\V3\\simulation\\isaac_sim_loader.py
    """
    try:
        from omni.isaac.kit import SimulationApp
        kit = SimulationApp({"headless": False})
        import omni.kit.commands
        from omni.isaac.core import World
        from omni.isaac.core.robots import Robot
        from omni.isaac.core.utils.stage import add_reference_to_stage
        from omni.isaac.urdf import _urdf
    except ImportError:
        print("[!] Note: This script is intended to be executed within the NVIDIA Isaac Sim environment.")
        print("    Run with: '<isaac_sim_root>/python.bat isaac_sim_loader.py' or through Isaac Sim Script Editor.")
        return

    print("============================================================")
    print(" NVIDIA ISAAC SIM - SO-101 LOADER & DIGITAL TWIN BRIDGE")
    print("============================================================")
    print(f"[*] Importing URDF: {urdf_path}")

    # Set URDF parse configuration
    urdf_interface = _urdf.acquire_urdf_interface()
    import_config = _urdf.ImportConfig()
    import_config.merge_fixed_joints = False
    import_config.fix_base = True
    import_config.make_default_prim = True
    import_config.self_collision = True
    import_config.create_physics_scene = True
    import_config.import_inertia_tensor = True
    import_config.default_drive_type = _urdf.UrdfJointTargetType.JOINT_DRIVE_POSITION

    # Import URDF to USD
    result, robot_prim_path = omni.kit.commands.execute(
        "URDFParseAndImportFile",
        urdf_path=urdf_path,
        import_config=import_config,
        dest_path=dest_usd_path,
    )

    world = World(stage_units_in_meters=1.0)
    world.scene.add_default_ground_plane()

    robot = world.scene.add(Robot(prim_path="/World/so101", name="so101_arm"))
    world.reset()

    print("[✓] SO-101 successfully imported into Isaac Sim stage!")
    print("    Active Joint names:")
    for name in robot.dof_names:
        print(f"     - {name}")

    print("[*] Starting Isaac Sim physics simulation loop...")
    while kit.is_running():
        world.step(render=True)

    kit.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Isaac Sim SO-101 Loader")
    parser.add_argument("--urdf", default=str(URDF_PATH), help="Path to so101.urdf")
    parser.add_argument("--usd", default="so101.usd", help="Output USD file path")
    args = parser.parse_args()

    import_so101_to_isaac_sim(urdf_path=args.urdf, dest_usd_path=args.usd)
