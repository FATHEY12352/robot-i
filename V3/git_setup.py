"""
=============================================================================
SO-101 / SO-ARM100 Git & GitHub Synchronization Tool
=============================================================================
Prepares, commits, and pushes V2 and V3 codebases to GitHub.

Usage:
  python git_setup.py
  python git_setup.py --remote https://github.com/username/SO-101-Studio.git
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"[!] Error: {res.stderr.strip()}")
    return res.returncode, res.stdout


def main():
    parser = argparse.ArgumentParser(description="Git & GitHub Sync for SO-101 V2/V3")
    parser.add_argument("--remote", help="GitHub repository URL (e.g. https://github.com/user/repo.git)")
    parser.add_argument("--branch", default="master", help="Git branch (default: master)")
    args = parser.parse_args()

    print("=" * 65)
    print("      SO-101 V2 & V3 GITHUB SYNCHRONIZATION")
    print("=" * 65)

    # 1. Stage all files
    run_cmd(["git", "add", "."])

    # 2. Check status
    _, status = run_cmd(["git", "status", "--short"])
    if status.strip():
        # Commit
        msg = "feat(v3): production-ready architecture, futuristic 3D studio, dual-arm teleop & simulation"
        run_cmd(["git", "commit", "-m", msg])
        print("[✓] Local commit created successfully!")
    else:
        print("[i] Working tree clean, no uncommitted changes.")

    # 3. Handle remote
    if args.remote:
        # Check existing remote
        _, remotes = run_cmd(["git", "remote"])
        if "origin" in remotes.split():
            run_cmd(["git", "remote", "set-url", "origin", args.remote])
        else:
            run_cmd(["git", "remote", "add", "origin", args.remote])

        print(f"[✓] Remote origin set to: {args.remote}")
        print(f"[*] Pushing to origin/{args.branch}...")
        ret, _ = run_cmd(["git", "push", "-u", "origin", args.branch])
        if ret == 0:
            print("[✓] Successfully pushed to GitHub!")
        else:
            print("[!] Push failed. Please verify credentials or run 'gh auth login'.")
    else:
        print("\n[NEXT STEP TO PUSH TO GITHUB]:")
        print("1. Create an empty repository on GitHub (e.g. https://github.com/user/SO-101-Studio)")
        print("2. Run the sync command with your repository URL:")
        print("   python V3/git_setup.py --remote https://github.com/YOUR_USERNAME/SO-101-Studio.git")
        print("=" * 65)


if __name__ == "__main__":
    main()
