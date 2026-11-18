"""
=============================================================================
SO-101 / SO-ARM100 V3 Studio Runner
=============================================================================
One-click runner to start the futuristic 3D Web Studio and hardware drivers.

Usage:
  python run_studio.py
  python run_studio.py --follower COM38 --leader COM39 --port 8080
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import webbrowser
from pathlib import Path

# Set up paths
V3_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(V3_DIR))

from web.server import V3StudioServer, HTTP_PORT


def main():
    parser = argparse.ArgumentParser(description="SO-101 V3 Futuristic Web Studio")
    parser.add_argument("--follower", default="COM38", help="Serial port for Follower arm (default: COM38)")
    parser.add_argument("--leader", default="COM39", help="Serial port for Leader arm (default: COM39)")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate (default: 1000000)")
    parser.add_argument("--port", type=int, default=HTTP_PORT, help="Web server port (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    print("=" * 65)
    print("      SO-101 / SO-ARM100 V3 FUTURISTIC ROBOTIC STUDIO")
    print("=" * 65)
    print(f"[*] Follower Port: {args.follower}")
    print(f"[*] Leader Port:   {args.leader}")
    print(f"[*] Baud Rate:     {args.baud} baud")
    print(f"[*] Web Interface: http://localhost:{args.port}")
    print("=" * 65)

    server = V3StudioServer(
        follower_port=args.follower,
        leader_port=args.leader,
        baudrate=args.baud,
        use_mock_fallback=True
    )

    if not args.no_browser:
        def _open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(f"http://localhost:{args.port}")
        import threading
        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        asyncio.run(server.run_async())
    except KeyboardInterrupt:
        print("\n[*] V3 Studio shutdown cleanly.")


if __name__ == "__main__":
    main()
