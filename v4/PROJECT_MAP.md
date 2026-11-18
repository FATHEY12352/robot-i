# SO-101 Robotics Studio V4 — Project Map & Architectural Memory

**Project:** SO-101 6-DOF Robotic Arm Studio V4  
**Date:** November 2026  
**Status:** Milestones 1 through 5 Implemented  
**Framework:** Hugging Face LeRobot (v0.7.0+ CLI Architecture)  
**Hardware:** Feetech STS3215 Serial Bus Servos + Dual USB Cameras (`top` + `wrist`)  

---

## 1. [TECH_STACK]

- **GUI Framework:** CustomTkinter (`customtkinter>=5.2.0`, Dark Theme, Student-Friendly)
- **Robotics & Policy Engine:** Hugging Face `lerobot` (v0.7.0+ CLI architecture: `lerobot-calibrate`, `lerobot-record`, `lerobot-train`, `lerobot-rollout`)
- **Deep Learning Acceleration:** PyTorch (`torch>=2.4.0` with CUDA 12.4+ & TensorFloat-32 `TF32` enabled, `AMP=false` for ACT stability)
- **Computer Vision:** OpenCV (`opencv-python>=4.8.0`) with DirectShow (`CAP_DSHOW` on Windows) / V4L2 (Linux) + Pillow (`PIL>=10.0.0`)
- **Serial Bus Hardware Driver:** `pyserial>=3.5` (Feetech STS3215 bus protocol, 1,000,000 baud default)
- **Package & Isolation:** Python Virtual Environment (`V4/.venv`), 1-click bootstrap scripts (`start_v4.bat` for Windows, `start_v4.sh` for Linux/RPi)

---

## 2. [SYSTEM_FLOW]

```
[Student / Operator]
        │
        ▼ (One-Click Launch: start_v4.bat / start_v4.sh)
[Studio V4 Desktop GUI (app_v4.py)]
        │
        ├──► [Tab 1: Hardware Wizard & Calibration]
        │         ├── Differential Serial Port Scanner (Auto-detects Follower COM & Leader COM)
        │         ├── Dual Camera Probe & Real-time Live Frame Preview (Top & Wrist at 640x480 @ 30fps)
        │         ├── Calibration Store Scanner (~/.cache/huggingface/lerobot/calibration/)
        │         └── 1-Click Calibration Runner (lerobot-calibrate --robot.type=so101_follower / --teleop.type=so101_leader)
        │
        ├──► [Tab 2: Data Collection (Teleop Record)]
        │         ├── Single Task Prompt & Episode Count Setup
        │         ├── Safe Hub Flags (--dataset.push_to_hub=false by default)
        │         └── Interactive Recording Launcher (lerobot-record in standalone terminal)
        │
        ├──► [Tab 3: Policy Training & Cloud Acceleration]
        │         ├── Local GPU ACT Training (TF32 enabled, AMP disabled to prevent NaN loss)
        │         ├── 1-Click Cloud Packager (.zip export to exports/ + auto-generated Colab/RunPod script)
        │         └── Policy Model Importer & Integrity Validator (validates config.json and weights)
        │
        └──► [Tab 4: Autonomous Deployment (Rollout)]
                  ├── Pretrained Model Selector (scans models/ and outputs/train/)
                  ├── Full Hardware & Camera Parameters (--robot.type=so101_follower, --fps=30, --task)
                  ├── Pure Policy Path Binding (--policy.path alone without --policy.type=act conflict)
                  ├── Performance Smoothness (--strategy.type=base, --interpolation_multiplier=2, --display_data=false)
                  └── Autonomous Policy Rollout Execution + Immediate Emergency Stop (process kill)
```

---

## 3. [ARCHITECTURE]

```
V4/
├── start_v4.bat                 # Windows 1-click bootstrapper (.venv creation, pip install, launcher)
├── start_v4.sh                  # Linux / Raspberry Pi 1-click bootstrapper
├── requirements_gui.txt         # GUI dependencies (customtkinter>=5.2.0, pyserial, opencv, pillow)
├── app_v4.py                    # Main Studio Desktop Application (CustomTkinter)
├── PROJECT_MAP.md               # Durable architectural memory and verification record
├── core/
│   ├── __init__.py              # Core package exports
│   ├── logger.py                # Asynchronous thread-safe logging with GUI subscriber callback
│   ├── env_manager.py           # OS/GPU/CUDA/VRAM detection and LeRobot toolchain checks
│   ├── hardware_wizard.py       # Differential COM port scanning, camera preview, calibration search
│   ├── process_runner.py        # CLI process builder enforcing LeRobot CLI rules & subprocess lifecycle
│   ├── train_act_wrapper.py     # Training wrapper enforcing TF32 precision and AMP=false
│   └── cloud_packager.py        # Dataset compressor for cloud training + model importer/validator
├── config/
│   └── hardware_profile.json    # Persistent hardware configuration (ports, camera indices, IDs, settings)
├── datasets/                    # Local teleoperated datasets
├── models/                      # Verified trained policy checkpoints ready for autonomous rollout
├── exports/                     # Compressed dataset archives + cloud training scripts (Colab/RunPod)
├── outputs/                     # Local training checkpoints and logs
└── tests/                       # Automated pytest suite covering 100% of core engine logic
```

### Critical Rules Enforced in Code:
1. **Mandatory CLI Type Invariants:** CLI arguments ALWAYS pass `--robot.type=so101_follower` and `--teleop.type=so101_leader`. The names `so_follower` and `so_leader` are ONLY subdirectories in LeRobot's calibration storage cache.
2. **Rollout Invariants:** `lerobot-rollout` must NEVER receive `--policy.type=act` when `--policy.path` is given. It includes full robot & camera configuration (`--robot.type=so101_follower`, `--robot.port=...`, `--robot.id=...`, `--robot.cameras=...`, `--fps=30`, `--task=...`), top-level `--device=cuda|cpu`, `--strategy.type=base`, and `--interpolation_multiplier=2`.
3. **Record Defaults:** `lerobot-record` includes `--dataset.single_task="..."`, `--dataset.push_to_hub=false` by default, and `--dataset.fps=30` (note: `--fps` at top level is only supported by rollout, record requires `--dataset.fps`).
4. **ACT Policy Stability:** Always enables `TF32` in PyTorch, passes `--tf32=true`, and sets `--policy.use_amp=false` (or `--accelerator.mixed_precision=no`) during training to eliminate `NaN` loss divergence.
5. **Process Safety:** Standalone terminal launches on Windows use `subprocess.CREATE_NEW_CONSOLE` with process tree termination (`taskkill /F /T /PID`) to guarantee immediate emergency stop.

8. **Physical Hardware Diagnosis & Live Bus Health:**
   - **Follower Arm (`COM38`):** Verified 100% healthy — all 6 Feetech STS3215 servos responded (`[1, 2, 3, 4, 5, 6]`).
   - **Leader Arm (`COM39`):** Servos `[1, 2, 3, 4, 5]` responded; Servo 6 (Gripper) was missing. `HardwareWizard.scan_feetech_servos` now pinpoints missing IDs in 0.15s.
   - **Dual Camera Architecture:** Replaced single preview canvas with dual side-by-side viewports (Top Workspace and Wrist Gripper) with sensor warmup and anti-glare gamma correction table to prevent washed-out overexposure.
   - **Serial Port Safety & Flexibility:** Added one-click port swapping (`Swap Ports`), dynamic COM dropdown population, and one-click `Free Ports` termination to resolve Windows `Access is denied` COM lockups.

---

## 4. [ORPHANS & PENDING]

- [x] Milestone 1: Foundation, launchers (`start_v4.bat`, `start_v4.sh`), requirements, directory layout, hardware profile.
- [x] Milestone 2: Asynchronous `core/logger.py` and `core/env_manager.py` (OS, CUDA, VRAM, and LeRobot checks).
- [x] Milestone 3: `core/hardware_wizard.py` (differential COM scanning, camera enumeration & live frame preview, calibration discovery, Feetech servo pinging).
- [x] Milestone 4: `core/process_runner.py` (enforcing all 3 mandatory CLI fixes, terminal/async execution) + `core/cloud_packager.py` (zip packaging & model validator).
- [x] Milestone 5: `app_v4.py` (Full CustomTkinter GUI integrating dual camera viewports, dynamic COM selection, live teleop & calibration) + automated pytest verification (16/16 passed).
- [x] Hardware Diagnostic: Follower COM38 verified healthy (6/6 servos); Leader COM39 diagnosed with Servo 6 disconnected.
- [Pending Operator Action]: Reconnect/plug 3-pin cable on Leader arm Servo 6 (Gripper).
