# SO-101 / SO-ARM100 NVIDIA Isaac Sim Setup & Workflow Guide

This guide details how to import, simulate, and train the **SO-101 (SO-ARM100)** dual-arm robotic system using **NVIDIA Isaac Sim (Omniverse)** and **Isaac Lab / Orbit**.

---

## 1. System Requirements

* **GPU**: NVIDIA RTX GPU (RTX 3070 / 4070 or higher recommended, minimum 8GB VRAM).
* **OS**: Windows 10/11 or Ubuntu 20.04/22.04 LTS.
* **Driver**: NVIDIA Display Driver 535.129.03+ (CUDA 12.x).
* **NVIDIA Omniverse Launcher**: Download and install from [nvidia.com/omniverse](https://www.nvidia.com/en-us/omniverse/).
* **Isaac Sim**: Install **Isaac Sim 4.0.0** or **4.1.0** via the Omniverse Launcher Exchange tab.

---

## 2. Importing the SO-101 Arm into Isaac Sim

The SO-101 robot is defined in `D:\projekt\ARM\V2\so101.urdf` with complete physical link mass, inertia tensors, and STL visual/collision geometry.

### Method A: One-Click Python Script
Run the automated loader script using Isaac Sim's internal Python binary:

```cmd
:: On Windows (Default Isaac Sim path)
cd "C:\Users\<USER>\AppData\Local\ov\pkg\isaac-sim-4.0.0"
python.bat "D:\projekt\ARM\V2\V3\simulation\isaac_sim_loader.py"
```

### Method B: Graphical URDF Importer (Isaac Sim GUI)
1. Launch **Isaac Sim** from Omniverse.
2. In the top menu, navigate to: `Isaac Utils -> Workflows -> URDF Importer`.
3. In the URDF Importer window:
   * **Input File**: Browse and select `D:\projekt\ARM\V2\so101.urdf`.
   * **Fix Base Link**: Checked (`True`).
   * **Self Collision**: Checked (`True`).
   * **Default Drive Type**: `Position`.
   * **Output Directory**: `D:\projekt\ARM\V2\V3\simulation\usd\`.
4. Click **Import**.
5. The full SO-101 digital twin will appear in the viewport with both gripper jaws properly articulated.

---

## 3. Joint Mapping & Drive Gains in Isaac Sim

When configuring drive parameters for the 6 revolute joints:

| Joint Name | URDF Joint | Real Motor ID | Type | Default Position (Home) | Stiffness (Kp) | Damping (Kd) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Shoulder Pan** | `shoulder_pan` | 1 | Revolute | `0.0 rad` (0°) | 400.0 | 40.0 |
| **Shoulder Lift** | `shoulder_lift` | 2 | Revolute | `-1.5708 rad` (-90°) | 800.0 | 60.0 |
| **Elbow Flex** | `elbow_flex` | 3 | Revolute | `1.5708 rad` (+90°) | 600.0 | 50.0 |
| **Wrist Flex** | `wrist_flex` | 4 | Revolute | `0.0 rad` (0°) | 300.0 | 25.0 |
| **Wrist Roll** | `wrist_roll` | 5 | Revolute | `0.0 rad` (0°) | 200.0 | 15.0 |
| **Gripper Jaw** | `gripper` | 6 | Revolute | `0.0 rad` (Open) | 150.0 | 10.0 |

---

## 4. Bridging Isaac Sim to Real Hardware & LeRobot

1. **Sim-to-Real Policy Evaluation**:
   Train your Actor-Critic (ACT) or Diffusion Policy in Isaac Sim / Isaac Lab with domain randomization.
2. **Real-time Digital Twin Streaming**:
   The V3 Web Studio sends live joint angles over WebSocket at 40Hz (`ws://localhost:8081`).
   A companion Isaac Sim extension can subscribe to the telemetry stream and mirror real-world arm motions inside the virtual stage with full physics and Ray Tracing.
