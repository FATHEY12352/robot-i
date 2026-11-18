"""
ACT Policy Training Launcher for SO-101 Robotics Studio V4.
Enforces TF32 acceleration on Ampere+ GPUs and disables AMP to prevent NaN loss explosions.
"""

from __future__ import annotations

import sys
import torch

def enable_tf32():
    """Enables TensorFloat-32 for faster matrix multiplication with FP32 stability."""
    try:
        torch.set_float32_matmul_precision("high")
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            print("[Studio V4] TF32 acceleration successfully enabled for PyTorch.")
    except Exception as e:
        print(f"[Studio V4] Notice: Could not set TF32 precision: {e}")

def main():
    enable_tf32()

    # Pass through arguments directly to lerobot-train
    try:
        from lerobot.scripts.lerobot_train import main as lerobot_train_main
        # Override sys.argv[0] to lerobot-train
        sys.argv[0] = "lerobot-train"
        lerobot_train_main()
    except ImportError:
        # Fallback to invoking lerobot CLI binary via subprocess if module import fails
        import subprocess
        cmd = ["lerobot-train"] + sys.argv[1:]
        print(f"[Studio V4] Invoking external CLI: {' '.join(cmd)}")
        res = subprocess.run(cmd)
        sys.exit(res.returncode)

if __name__ == "__main__":
    main()
