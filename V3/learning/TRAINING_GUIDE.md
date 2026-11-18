# SO-101 Learning Guide

## Kinesthetic teaching

1. Put the follower in a safe state and disable follower torque with `POST /api/arm/torque` and `{ "enable": false }` if it must be moved by hand.
2. Start recording from leader COM39 with `POST /api/trajectory/record/start` and optional `{ "hz": 50 }`.
3. Move the leader slowly through the desired task.
4. Stop and save the episode with `POST /api/trajectory/record/stop`; the response returns the JSON filename.
5. Inspect the JSON frames and calibration before follower playback. ID 6 is omitted if disconnected.

Keep the follower clear of people and hard stops. ID 6 may be absent on COM38 and must remain excluded from commands while it is disconnected.

## LeRobot teleoperation

Use the leader COM39 as the state source and follower COM38 as the action target. At each control step, read raw ticks for IDs 1-5, preserve the shortest 12-bit wraparound path, and send a synchronized write to the follower. Store raw ticks as `observation.state` and `action`; convert to degrees only for inspection and model metadata.

## ACT training

Export recorded episodes into a LeRobot dataset with six-dimensional state/action vectors. Start with a low episode count and validate that the policy reaches a neutral target in simulation before connecting torque. Example dimensions:

- `observation.state`: float32 `[6]`
- `action`: float32 `[6]`
- camera observations: optional image streams

Train with conservative action chunking and validate each checkpoint on held-out episodes.

## Diffusion Policy

Normalize positions using the calibrated min/max ticks per joint. Keep the gripper channel masked when follower ID 6 is offline. Use fixed-rate samples, synchronized timestamps, and explicit episode boundaries. Reject frames containing missing active joints rather than silently interpolating hardware failures.

## Isaac Sim and URDF

1. Import the project `so101.urdf` into Isaac Sim.
2. Verify the six revolute joints and their limits in radians.
3. Use the same joint order and home pose as `CalibrationStore`.
4. Set the simulated control action to raw ticks through a conversion layer.
5. Validate forward-kinematics positions against `SO101Kinematics` before policy training.
6. Add the STL assets as visual meshes and set collision meshes separately where needed.

The physical system runs at 1,000,000 baud. Simulation should preserve the same six-joint ordering, timing, and 5-DOF fallback behavior.
