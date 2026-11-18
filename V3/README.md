# SO-101 / SO-ARM100 V3

V3 software for a dual-arm system driven by six Feetech STS3215 smart serial-bus servos per arm. Position commands are raw 12-bit ticks (0–4095 represents one 360° encoder revolution), not PWM.

## Hardware map and safety

| Arm | Port | Servo IDs | Notes |
|---|---|---|---|
| Follower | COM38 | 1–6 | ID 6 may be unwired; it is marked `DISCONNECTED` and omitted from commands. |
| Leader | COM39 | 1–6 | Used as the trajectory recording source. |

The bus runs at 1,000,000 baud. `V3/hardware/` is the protected protocol, driver, device-registry, and controller layer. Keep the arm clear, verify the calibration and limits, and test with torque disabled before enabling motion.

## Install

From `D:\projekt\ARM\V2` using the project virtual environment:

```powershell
.venv\Scripts\python.exe -m pip install -r V3\requirements.txt
```

The original V2 files are not part of V3 changes. Run tests from the V3 directory:

```powershell
cd V3
..\.venv\Scripts\python.exe -m pytest tests/ -q
```

## Web Studio

From `D:\projekt\ARM\V2\V3`:

```powershell
..\.venv\Scripts\python.exe -m web.server --follower COM38 --leader COM39
```

For UI/API work without opening serial ports, add `--demo`. The Studio listens on port 8080, streams telemetry over `/ws` at 30 Hz, and serves the browser UI at `/`.

REST API:

- `POST /api/servo/{id}/position` — body accepts `ticks` or `degrees`, and optional `speed`.
- `POST /api/arm/home` and `/api/arm/torque` — follower home and torque control.
- `POST /api/test/sequential` — per-servo connectivity/status report.
- `POST /api/trajectory/record/start` (`{"hz":50}`) and `/api/trajectory/record/stop`.
- `POST /api/trajectory/play` (`file` optional for latest recording; `speed_factor`, `loop`). Stop at `/api/trajectory/play/stop`.
- `POST /api/ik/move` — target `x`, `y`, `z` in millimeters with optional `roll`, `pitch`, `yaw` in degrees.
- `GET/POST /api/calibration`; capture current joint limits at `/api/calibration/{joint}/min`, `/max`, or `/zero`.
- `GET /api/servo/scan` — scan follower bus IDs.

The Studio has raw-tick joint controls, speed controls, home/torque/test actions, trajectory record/play, calibration export, telemetry cards, and click-to-IK on the 3D view. Offline servos are displayed as disconnected; do not connect or enable torque until the mechanism is physically safe.

## Kinematics and calibration

`kinematics/so101_kinematics.py` supplies standard-DH forward/inverse kinematics (SciPy least-squares IK), degree/tick conversion, and physical degree limits:

- J1 base: −150° to 150°; J2 shoulder: −105° to 105°; J3 elbow: −95° to 95°.
- J4 wrist pitch: −105° to 105°; J5 wrist roll: −90° to 90°; J6 gripper: 0° to 95°.

The folded home pose is `{1: 0, 2: -90, 3: 90, 4: 0, 5: 0, 6: 0}` degrees. `calibration/calibration_store.py` stores per-arm/per-joint `min_ticks`, `max_ticks`, and `zero_ticks` in `calibration/calibration.json`; validate the saved limits before enabling torque.

## Trajectory recording and playback

`motion/trajectory_engine.py` records timestamped `joint_ticks` frames from the leader in a background thread. Trajectory JSON is stored under `V3/trajectories/` by default (ignored by git). Playback interpolates at approximately 100 Hz, takes the shortest path across the 0/4095 seam, and filters IDs known to be offline. Public entry points are `record_start(arm_controller, hz=50)`, `record_stop()`, `save_trajectory()`, `load_trajectory()`, and `play_trajectory()`.

## Learning / LeRobot

Run `python -m learning.setup_lerobot` to check for an optional LeRobot installation and emit the sample YAML configuration. The package is not required for hardware control. `learning/TRAINING_GUIDE.md` covers kinesthetic teaching, LeRobot teleoperation, ACT, Diffusion Policy, and Isaac Sim/URDF setup. Treat learned actions as untrusted: validate limits and test in simulation before enabling hardware torque.
