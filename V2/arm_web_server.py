"""
====================================================================
SO-100 / SO-101 3D Web Studio Server (Fast Three.js Digital Twin)
====================================================================
Runs an asynchronous WebSocket + HTTP server on http://localhost:8080.
Connects directly to the physical arm on COM38 and streams 3D joint
angles, calibration data, and lead-through recording/playback.
"""

import os
import sys
import json
import asyncio
import webbrowser
import websockets
from http.server import SimpleHTTPRequestHandler
import socketserver
import threading
import time

from so101_arm import SO101Arm
from calibration_manager import CalibrationManager
from trajectory_recorder import TrajectoryRecorder

HTTP_PORT = 8080
WS_PORT = 8081

HTML_PATH = os.path.join(os.path.dirname(__file__), "arm_web_studio.html")

class ArmWebStudioServer:
    def __init__(self):
        self.arm = SO101Arm("COM38", baudrate=1000000)
        self.calib = CalibrationManager()
        self.recorder = TrajectoryRecorder(self.arm)

        self.connected_clients = set()
        self.current_states = {}
        self.voltage = 0.0

    def start_http(self):
        """Serve the static 3D Web studio HTML on port 8080."""
        class Handler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path in ["/", "/index.html"]:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    with open(HTML_PATH, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    super().do_GET()

            def log_message(self, format, *args):
                pass # Silent logging

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", HTTP_PORT), Handler) as httpd:
            print(f"[✓] 3D Web Studio UI running at: http://localhost:{HTTP_PORT}")
            httpd.serve_forever()

    async def ws_handler(self, websocket):
        """Handle incoming WebSocket connections from 3D browser client."""
        self.connected_clients.add(websocket)
        print(f"[+] 3D Browser Connected! Total viewers: {len(self.connected_clients)}")

        # Send initial firmware and model information
        try:
            fw_info = self.arm.get_firmware_versions()
            await websocket.send(json.dumps({
                "type": "init_info",
                "firmware": fw_info,
                "model": "STS3215",
                "baud": 1000000
            }))
        except Exception:
            pass

        try:
            async for message in websocket:
                data = json.loads(message)
                cmd = data.get("cmd")

                if cmd == "free_drive":
                    enable = data.get("enable", False)
                    if enable:
                        self.arm.disable_all_torque()
                        print("[*] Free Drive ENABLED: Hand teaching active.")
                    else:
                        self.arm.enable_all_torque()
                        print("[*] Free Drive DISABLED: Holding position.")

                elif cmd == "start_record":
                    self.recorder.start_recording()
                    print("[🔴] Continuous trajectory recording STARTED...")

                elif cmd == "stop_record":
                    path = self.recorder.stop_recording()
                    print(f"[⏹] Trajectory saved: {path}")

                elif cmd == "play_record":
                    print("[▶] Playing recorded trajectory on real robot...")
                    def run_play():
                        self.recorder.play(self.recorder.frames, loop=False)
                    threading.Thread(target=run_play, daemon=True).start()

                elif cmd == "set_limit":
                    joint_id = int(data.get("joint", 1))
                    l_type = data.get("type", "min")
                    raw = self.current_states.get(joint_id, {}).get("raw_pos", 2048)
                    if l_type == "min":
                        self.calib.set_min(joint_id, raw)
                        print(f"[Calib] Joint {joint_id} MIN limit captured: {raw}")
                    else:
                        self.calib.set_max(joint_id, raw)
                        print(f"[Calib] Joint {joint_id} MAX limit captured: {raw}")

                elif cmd == "save_calibration":
                    self.calib.save()

                elif cmd == "center_servos":
                    print("[*] Centering all 6 servos to 2048 (Half-Turn Neutral Home)...")
                    res = self.arm.center_all_servos()
                    print(f"[✓] Centered to 2048: {res}")

                elif cmd == "pose":
                    p_name = data.get("name")
                    if p_name == "home":
                        self.arm.smooth_move_pose({1: 180, 2: 180, 3: 180, 4: 180, 5: 180, 6: 90}, duration=1.2)
                    elif p_name == "rest":
                        self.arm.smooth_move_pose({1: 180, 2: 90, 3: 270, 4: 180, 5: 180, 6: 45}, duration=1.2)
                    elif p_name == "wave":
                        threading.Thread(target=self._wave_demo, daemon=True).start()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)
            print(f"[-] Browser Disconnected. Remaining viewers: {len(self.connected_clients)}")

    def _wave_demo(self):
        self.arm.smooth_move_pose({1: 180, 2: 150, 3: 200, 4: 180, 5: 180, 6: 120}, duration=1.2)
        for _ in range(3):
            self.arm.move_joint(5, 225, speed=600)
            time.sleep(0.35)
            self.arm.move_joint(5, 135, speed=600)
            time.sleep(0.35)
        self.arm.move_joint(5, 180, speed=400)

    async def telemetry_loop(self):
        """Poll robot at 30Hz and broadcast telemetry to all browser clients."""
        while True:
            if self.arm.is_connected:
                states = self.arm.get_all_states()
                if states:
                    self.current_states = states
                    if 1 in states:
                        self.voltage = states[1]["voltage"]

                    # If recording, record frame!
                    if self.recorder.is_recording:
                        self.recorder.record_step(states)
                        n = len(self.recorder.frames)
                        t = self.recorder.frames[-1]["t"] if self.recorder.frames else 0.0
                        status_msg = json.dumps({"type": "rec_status", "frames": n, "sec": round(t, 1)})
                        for ws in list(self.connected_clients):
                            try:
                                await ws.send(status_msg)
                            except Exception:
                                pass

                    # Broadcast full live telemetry to Three.js scene & UI dashboard
                    angles = {sid: s["angle"] for sid, s in states.items()}
                    raws = {sid: s["raw_pos"] for sid, s in states.items()}

                    msg = json.dumps({
                        "type": "telemetry",
                        "angles": angles,
                        "raws": raws,
                        "voltage": self.voltage,
                        "states": states
                    })

                    for ws in list(self.connected_clients):
                        try:
                            await ws.send(msg)
                        except Exception:
                            pass

            await asyncio.sleep(0.033) # ~30 Hz

    def run(self):
        print("=" * 65)
        print("      SO-101 3D DIGITAL TWIN & TEACHING STUDIO SERVER")
        print("=" * 65)
        print("[*] Connecting to physical arm on COM38...")
        if self.arm.connect():
            print("[✓] Connected to COM38 at 1,000,000 baud!")
        else:
            print("[!] Could not connect to COM38. Running in offline/preview mode.")

        # Start HTTP server thread
        t_http = threading.Thread(target=self.start_http, daemon=True)
        t_http.start()

        time.sleep(0.5)
        print(f"[*] Opening 3D Studio in your browser: http://localhost:{HTTP_PORT}")
        webbrowser.open(f"http://localhost:{HTTP_PORT}")

        async def main_async():
            try:
                async with websockets.serve(self.ws_handler, "0.0.0.0", WS_PORT):
                    print(f"[✓] WebSocket telemetry server listening on port {WS_PORT}")
                    await self.telemetry_loop()
            except (asyncio.CancelledError, KeyboardInterrupt):
                pass

        try:
            asyncio.run(main_async())
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            print("\n[*] Shutting down server and releasing COM port...")
            self.arm.close()
            print("[✓] Server stopped cleanly.")

if __name__ == "__main__":
    server = ArmWebStudioServer()
    server.run()
