#!/usr/bin/env python3
"""
SO-101 / SO-ARM100 V3 ACT Policy Training Runner
Configured for NVIDIA RTX 4050 (6GB VRAM) and 50-episode Pick & Place dataset.
"""

import os
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Train LeRobot ACT policy on SO-101 dataset")
    parser.add_argument("--steps", type=int, default=30000, help="Total training steps (default: 30,000)")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size (default: 8 for 6GB VRAM)")
    parser.add_argument("--save-freq", type=int, default=5000, help="Checkpoint save frequency (default: 5,000)")
    parser.add_argument("--log-freq", type=int, default=100, help="Log metrics frequency (default: 100)")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint if exists")
    args = parser.parse_args()

    v3_dir = Path(__file__).resolve().parents[1]
    workspace_dir = v3_dir.parent

    # Look for dataset in V3/datasets first, fallback to root/datasets
    if (v3_dir / "datasets" / "so101_pick_place").exists():
        dataset_dir = v3_dir / "datasets" / "so101_pick_place"
    else:
        dataset_dir = workspace_dir / "datasets" / "so101_pick_place"

    output_dir = v3_dir / "outputs" / "train" / "act_so101_pick_place"

    if not dataset_dir.exists():
        print(f"[ERROR] Dataset directory not found: {dataset_dir}")
        sys.exit(1)

    print("=" * 65)
    print("      SO-101 LE ROBOT ACT POLICY TRAINING (GPU / CUDA)")
    print("=" * 65)
    print(f"[*] Dataset:    {dataset_dir}")
    print(f"[*] Output Dir: {output_dir}")
    print(f"[*] Batch Size: {args.batch_size}")
    print(f"[*] Steps:      {args.steps}")
    print(f"[*] Precision:  fp16 (Mixed Precision via AMP)")
    print(f"[*] Device:     CUDA (NVIDIA GeForce RTX 4050)")
    print("=" * 65)

    from lerobot.scripts.lerobot_train import main as lerobot_train_main

    train_argv = [
        "lerobot-train",
        f"--dataset.repo_id=voidstore/so101_pick_place",
        f"--dataset.root={dataset_dir.as_posix()}",
        "--policy.type=act",
        "--policy.push_to_hub=false",
        f"--output_dir={output_dir.as_posix()}",
        "--job_name=act_so101_pick_place",
        f"--batch_size={args.batch_size}",
        f"--steps={args.steps}",
        f"--save_freq={args.save_freq}",
        f"--log_freq={args.log_freq}",
        "--save_checkpoint=true",
        "--save_checkpoint_to_hub=false",
        "--trackio.enable=false",
        "--num_workers=0",
        "--accelerator.mixed_precision=fp16",
    ]

    if args.resume:
        train_argv.append("--resume=true")

    sys.argv = train_argv
    try:
        lerobot_train_main()
    except KeyboardInterrupt:
        print("\n[*] Training interrupted by user. Latest checkpoint preserved in output directory.")
    except Exception as e:
        print(f"\n[ERROR] Training error: {e}")
        raise

if __name__ == "__main__":
    main()
