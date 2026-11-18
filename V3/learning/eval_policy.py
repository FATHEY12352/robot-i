#!/usr/bin/env python3
"""
SO-101 / SO-ARM100 Autonomous Policy Evaluator & Rollout Runner
Runs a trained ACT policy on the real Follower arm with Top and Wrist OpenCV cameras.
"""

import sys
import time
import argparse
import logging
from pathlib import Path
import cv2
import torch
import numpy as np

# Add V3 to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hardware.bus_driver import BusDriver
from hardware.sts3215_protocol import REG_TORQUE_ENABLE
from calibration.calibration_store import CalibrationStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eval_policy")

def capture_frame(cap, width=640, height=480):
    ret, frame = cap.read()
    if not ret or frame is None:
        return np.zeros((height, width, 3), dtype=np.uint8)
    return frame

def frame_to_tensor(frame):
    # Convert BGR (OpenCV) to RGB, normalize to [0, 1], shape (1, 3, H, W)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    return tensor.unsqueeze(0)

def main():
    parser = argparse.ArgumentParser(description="Evaluate trained ACT policy on SO-101 arm")
    default_ckpt = Path(__file__).resolve().parents[1] / "outputs" / "train" / "act_so101_pick_place" / "checkpoints" / "last" / "pretrained_model"
    parser.add_argument("--checkpoint", type=str, default=str(default_ckpt),
                        help="Path to pretrained model directory")
    parser.add_argument("--port", type=str, default="COM38", help="Follower serial port (COM38)")
    parser.add_argument("--top-cam", type=int, default=0, help="Top camera index (default: 0)")
    parser.add_argument("--wrist-cam", type=int, default=1, help="Wrist camera index (default: 1)")
    parser.add_argument("--fps", type=float, default=30.0, help="Control loop frequency in Hz")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending commands to physical motors")
    parser.add_argument("--max-steps", type=int, default=750, help="Max rollout steps (~25 seconds at 30 fps)")
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error(f"Checkpoint path not found: {checkpoint_path}")
        logger.info("Please train the policy first or specify a valid checkpoint using --checkpoint")
        sys.exit(1)

    logger.info("================================================================")
    logger.info("     SO-101 AUTONOMOUS POLICY EVALUATION / REAL ROLLOUT")
    logger.info("================================================================")
    logger.info(f"[*] Checkpoint: {checkpoint_path}")
    logger.info(f"[*] Follower:   {args.port}")
    logger.info(f"[*] Cameras:    Top #{args.top_cam}, Wrist #{args.wrist_cam}")
    logger.info(f"[*] Dry run:    {args.dry_run}")
    logger.info("================================================================")

    # 1. Load LeRobot Pretrained ACT Policy
    from lerobot.policies.act.modeling_act import ACTPolicy
    logger.info("Loading ACT Policy from checkpoint...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy = ACTPolicy.from_pretrained(str(checkpoint_path))
    policy.to(device)
    policy.eval()
    policy.reset()
    logger.info(f"[✓] Policy successfully loaded on {device}")

    # 2. Initialize Cameras
    logger.info("Opening OpenCV camera streams...")
    top_cap = cv2.VideoCapture(args.top_cam, cv2.CAP_DSHOW)
    top_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    top_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    top_cap.set(cv2.CAP_PROP_FPS, 30)

    wrist_cap = cv2.VideoCapture(args.wrist_cam, cv2.CAP_DSHOW)
    wrist_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    wrist_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    wrist_cap.set(cv2.CAP_PROP_FPS, 30)

    # 3. Connect to Follower arm
    bus = None
    active_servos = [1, 2, 3, 4, 5]
    if not args.dry_run:
        try:
            bus = BusDriver(port=args.port, baudrate=1000000, timeout=0.05)
            bus.connect()
            # Check ID 6
            if bus.ping(6):
                active_servos.append(6)
            logger.info(f"[✓] Follower arm connected on {args.port} (active IDs: {active_servos})")
            # Enable torque
            for sid in active_servos:
                bus.write_register(sid, REG_TORQUE_ENABLE, 1)
        except Exception as e:
            logger.error(f"Failed to connect to Follower arm: {e}")
            sys.exit(1)

    calib = CalibrationStore()
    calib.load()

    dt = 1.0 / args.fps
    logger.info(f"Starting autonomous rollout for up to {args.max_steps} steps. Press Ctrl+C to abort.")

    try:
        for step in range(args.max_steps):
            t_start = time.perf_counter()

            # Read current arm positions (raw ticks)
            state_vals = [2048] * 6
            if bus and not args.dry_run:
                for idx, sid in enumerate(active_servos):
                    pos = bus.read_position(sid)
                    if pos is not None:
                        state_vals[sid - 1] = pos

            # Capture cameras
            top_frame = capture_frame(top_cap)
            wrist_frame = capture_frame(wrist_cap)

            top_tensor = frame_to_tensor(top_frame).to(device)
            wrist_tensor = frame_to_tensor(wrist_frame).to(device)
            state_tensor = torch.tensor([state_vals], dtype=torch.float32, device=device)

            batch = {
                "observation.images.top": top_tensor,
                "observation.images.wrist": wrist_tensor,
                "observation.state": state_tensor,
            }

            with torch.no_grad():
                action = policy.select_action(batch)
                # action shape: (1, 6) or (6,)
                action_np = action.squeeze().cpu().numpy()

            target_ticks = [int(round(float(v))) for v in action_np[:len(active_servos)]]

            # Send action to motors
            if bus and not args.dry_run:
                sync_items = []
                for idx, sid in enumerate(active_servos):
                    target = target_ticks[idx]
                    # Clamp to calibrated bounds
                    bounds = calib.get_joint_bounds(sid)
                    target_clamped = max(bounds.min_ticks, min(bounds.max_ticks, target))
                    sync_items.append((sid, target_clamped, 0, 0)) # pos, speed=0 (max), acc=0
                bus.sync_write_position(sync_items)

            if step % 30 == 0:
                logger.info(f"[Step {step:04d}/{args.max_steps}] Action ticks: {target_ticks}")

            # Maintain control frequency
            elapsed = time.perf_counter() - t_start
            sleep_time = dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("\n[*] Rollout stopped by user.")
    finally:
        top_cap.release()
        wrist_cap.release()
        if bus and not args.dry_run:
            logger.info("Releasing torque and closing serial port...")
            for sid in active_servos:
                try:
                    bus.write_register(sid, REG_TORQUE_ENABLE, 0)
                except Exception:
                    pass
            bus.disconnect()
        logger.info("[✓] Shutdown complete.")

if __name__ == "__main__":
    main()
