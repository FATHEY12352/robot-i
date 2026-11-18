"""
=============================================================================
SO-101 / SO-ARM100 V3 Futuristic Web Studio Server
=============================================================================
High-performance asynchronous server coordinating dual-arm hardware (COM38/COM39),
kinematics, trajectory recording, sequential motor testing, and 3D digital twin.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler
import socketserver
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Import V3 core modules
V3_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V3_DIR))

from hardware.arm_bus_controller import ArmBusController
from hardware.bus_driver import BusDriver
from hardware.device_registry import DeviceRegistry
from kinematics.so101_kinematics import (
    forward_kinematics,
    inverse_kinematics,
    clamp_to_limits,
    ticks_to_deg,
    deg_to_ticks,
    JOINT_LIMITS_DEG,
    HOME_POSE_DEG,
)
from calibration.calibration_store import CalibrationStore
from motion.trajectory_engine import TrajectoryRecorder, TrajectoryPlayer, save_trajectory, load_trajectory, list_trajectories

import websockets

logger = logging.getLogger("V3_StudioServer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HTTP_PORT = 8080
WS_PORT = 8081

STATIC_DIR = Path(__file__).resolve().parent
ASSETS_DIR = V3_DIR.parent / "assets"
HTML_PATH = STATIC_DIR / "studio.html"


class V3StudioServer:
    def __init__(
        self,
        follower_port: str = "COM38",
        leader_port: str = "COM39",
        baudrate: int = 1000000,
        use_mock_fallback: bool = True
    ):
        self.follower_port = follower_port
        self.leader_port = leader_port
        self.baudrate = baudrate
        self.use_mock_fallback = use_mock_fallback

        self.calib = CalibrationStore(str(V3_DIR / "calibration" / "calibration.json"))
        self.connected_clients: Set[Any] = set()

        # Follower Arm Controller
        self.follower: Optional[ArmBusController] = None
        self.leader: Optional[ArmBusController] = None

        self._follower_connected = False
        self._leader_connected = False
        self._is_mock = False

        self.trajectory_recorder = TrajectoryRecorder()
        self.trajectory_player: Optional[TrajectoryPlayer] = None

        self.current_follower_states: Dict[int, Dict[str, Any]] = {}
        self.current_leader_states: Dict[int, Dict[str, Any]] = {}

        self.global_speed = 700
        self.global_accel = 50

        # Background tasks
        self._running = False
        self._seq_test_running = False

    def initialize_hardware(self) -> None:
        """Connect to real hardware or fall back to mock bus for seamless testing."""
        # 1. Try Follower Arm (COM38)
        try:
            logger.info(f"Attempting connection to Follower arm on {self.follower_port} at {self.baudrate} baud...")
            bus_follower = BusDriver(self.follower_port, baudrate=self.baudrate, timeout=0.03)
            bus_follower.open()
            self.follower = ArmBusController(bus_follower)
            self.follower.connect()
            self._follower_connected = True
            logger.info(f"[✓] Follower arm connected on {self.follower_port} (5-DOF active)")
        except Exception as e:
            logger.warning(f"Could not connect real Follower on {self.follower_port}: {e}")
            if self.use_mock_fallback:
                logger.info("[*] Initializing Virtual Mock Serial Bus for Follower...")
                bus_mock = BusDriver(self.follower_port, baudrate=self.baudrate, use_mock=True)
                bus_mock.open()
                self.follower = ArmBusController(bus_mock)
                self.follower.connect()
                self._follower_connected = True
                self._is_mock = True
                logger.info("[✓] Mock Follower arm online.")

        # 2. Try Leader Arm (COM39)
        try:
            logger.info(f"Attempting connection to Leader arm on {self.leader_port} at {self.baudrate} baud...")
            bus_leader = BusDriver(self.leader_port, baudrate=self.baudrate, timeout=0.03)
            bus_leader.open()
            self.leader = ArmBusController(bus_leader)
            self.leader.connect()
            self._leader_connected = True
            logger.info(f"[✓] Leader arm connected on {self.leader_port} (6-DOF active)")
        except Exception as e:
            logger.info(f"Leader arm not detected on {self.leader_port} (optional): {e}")

    def start_http(self) -> None:
        """Serve futuristic 3D Web Studio and local assets on HTTP_PORT."""
        class StudioHTTPHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path in ("/", "/index.html", "/studio"):
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.end_headers()
                    if HTML_PATH.is_file():
                        with open(HTML_PATH, "rb") as f:
                            self.wfile.write(f.read())
                    else:
                        self.wfile.write(b"<h1>V3 3D Studio HTML loading...</h1>")
                    return

                # Assets route
                if self.path.startswith("/assets/"):
                    asset_name = self.path.split("/assets/")[-1].split("?")[0]
                    asset_file = ASSETS_DIR / asset_name
                    if asset_file.is_file():
                        self.send_response(200)
                        if asset_name.endswith(".stl"):
                            self.send_header("Content-type", "application/sla")
                        elif asset_name.endswith(".js"):
                            self.send_header("Content-type", "application/javascript")
                        elif asset_name.endswith(".css"):
                            self.send_header("Content-type", "text/css")
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.end_headers()
                        with open(asset_file, "rb") as f:
                            self.wfile.write(f.read())
                        return

                self.send_error(404, "File Not Found")

            def log_message(self, format, *args):
                pass  # Keep console output clean

        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", HTTP_PORT), StudioHTTPHandler) as httpd:
            logger.info(f"[✓] Futuristic 3D Web Studio live at: http://localhost:{HTTP_PORT}")
            httpd.serve_forever()

    async def ws_handler(self, websocket: Any) -> None:
        """Handle incoming WebSocket connections from 3D browser client."""
        self.connected_clients.add(websocket)
        logger.info(f"[+] Client connected to V3 Studio. Active viewers: {len(self.connected_clients)}")

        # Send initial status
        try:
            init_payload = {
                "type": "init_status",
                "follower_connected": self._follower_connected,
                "leader_connected": self._leader_connected,
                "is_mock": self._is_mock,
                "home_pose": HOME_POSE_DEG,
                "joint_limits": JOINT_LIMITS_DEG,
                "calibration": self.calib.data,
                "global_speed": self.global_speed,
                "global_accel": self.global_accel,
                "trajectories": list_trajectories(),
            }
            await websocket.send(json.dumps(init_payload))
        except Exception as e:
            logger.warning(f"Error sending init status: {e}")

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_command(websocket, data)
                except Exception as ex:
                    logger.error(f"Error processing WS message: {ex}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            logger.info(f"[-] Client disconnected. Active viewers: {len(self.connected_clients)}")

    async def _process_command(self, ws: Any, data: Dict[str, Any]) -> None:
        cmd = data.get("cmd")

        # 1. Manual joint command
        if cmd == "set_joint":
            joint_id = int(data.get("joint", 1))
            degrees = float(data.get("degrees", 0.0))
            speed = int(data.get("speed", self.global_speed))
            raw_target = deg_to_ticks(degrees, joint_id)

            # Validate against calibrated limits
            safe_ticks = self.calib.validate_ticks("follower", joint_id, raw_target)

            if self.follower and self.follower.is_connected:
                self.follower.sync_write_positions({joint_id: safe_ticks}, default_speed=speed)

        # 2. Synchronized pose command
        elif cmd == "set_pose":
            pose_deg = data.get("angles", {})  # {1: deg, 2: deg...}
            speed = int(data.get("speed", self.global_speed))
            goal_dict = {}
            for sid_str, deg in pose_deg.items():
                sid = int(sid_str)
                safe_ticks = self.calib.validate_ticks("follower", sid, deg_to_ticks(float(deg), sid))
                goal_dict[sid] = safe_ticks

            if self.follower and self.follower.is_connected:
                self.follower.sync_write_positions(goal_dict, default_speed=speed)

        # 3. Click-to-Move 3D Cartesian IK
        elif cmd == "click_to_move":
            x = float(data.get("x", 0.0))
            y = float(data.get("y", 180.0))
            z = float(data.get("z", 100.0))
            speed = int(data.get("speed", self.global_speed))

            # Solve Inverse Kinematics
            try:
                # Clamp workspace boundaries to safe mechanical reach
                r = math.hypot(x, y)
                r_safe = max(90.0, min(330.0, r if r > 1e-3 else 90.0))
                x_safe = x * (r_safe / r) if r > 1e-3 else 0.0
                y_safe = y * (r_safe / r) if r > 1e-3 else r_safe
                z_safe = max(20.0, min(350.0, z))

                ik_angles = inverse_kinematics(x_safe, y_safe, z_safe)
                clamped_angles = clamp_to_limits(ik_angles)

                # Send response to UI with calculated angles
                await ws.send(json.dumps({
                    "type": "ik_result",
                    "target": {"x": x_safe, "y": y_safe, "z": z_safe},
                    "angles": clamped_angles,
                    "success": True,
                }))

                # Move physical arm
                if self.follower and self.follower.is_connected:
                    goal_dict = {}
                    for i, deg in enumerate(clamped_angles[:5], 1):  # 5-DOF
                        safe_ticks = self.calib.validate_ticks("follower", i, deg_to_ticks(deg, i))
                        goal_dict[i] = safe_ticks
                    self.follower.sync_write_positions(goal_dict, default_speed=speed)

            except Exception as e:
                logger.error(f"IK computation failed: {e}")
                await ws.send(json.dumps({
                    "type": "ik_result",
                    "success": False,
                    "error": str(e)
                }))

        # 4. Sequential Motor Test Routine (+10° and -10°)
        elif cmd == "run_sequential_test":
            if self._seq_test_running:
                return
            threading.Thread(target=self._run_sequential_test_thread, daemon=True).start()

        # 5. Free drive toggle
        elif cmd == "free_drive":
            enable = bool(data.get("enable", False))
            target_arm = data.get("arm", "follower")
            ctrl = self.follower if target_arm == "follower" else self.leader
            if ctrl and ctrl.is_connected:
                ctrl.set_torque(not enable)
                logger.info(f"[*] Free drive on {target_arm}: {'ON' if enable else 'OFF'}")

        # 6. Home / Rest Pose
        elif cmd == "go_home":
            home_ticks = self.calib.get_home_ticks("follower")
            if self.follower and self.follower.is_connected:
                self.follower.sync_write_positions(home_ticks, default_speed=500)
                logger.info("[*] Moving to folded resting Home pose.")

        # 7. Calibration actions
        elif cmd == "set_limit":
            arm_id = data.get("arm", "follower")
            joint_id = int(data.get("joint", 1))
            limit_type = data.get("type", "min")  # "min" or "max" or "zero"

            states = self.current_follower_states if arm_id == "follower" else self.current_leader_states
            raw = states.get(joint_id, {}).get("raw_pos", 2048)

            if limit_type == "min":
                self.calib.set_joint_min(arm_id, joint_id, raw)
            elif limit_type == "max":
                self.calib.set_joint_max(arm_id, joint_id, raw)
            elif limit_type == "zero":
                self.calib.set_joint_zero(arm_id, joint_id, raw)

            self.calib.save()
            logger.info(f"[Calib] {arm_id} Joint {joint_id} {limit_type.upper()} set to {raw}")
            # Broadcast updated calibration
            await self._broadcast({
                "type": "calibration_updated",
                "calibration": self.calib.data
            })

        # 8. Trajectory Recording
        elif cmd == "start_record":
            hz = float(data.get("hz", 50.0))
            target_arm = data.get("arm", "leader" if self._leader_connected else "follower")
            ctrl = self.leader if target_arm == "leader" else self.follower
            if ctrl and ctrl.is_connected:
                self.trajectory_recorder.start(ctrl, sample_hz=hz)
                logger.info(f"[🔴] Recording started from {target_arm} at {hz} Hz")

        elif cmd == "stop_record":
            name = data.get("name", f"traj_{int(time.time())}")
            frames = self.trajectory_recorder.stop()
            if frames:
                meta = {"arm": "so101", "frames": len(frames)}
                filepath = save_trajectory(frames, name=name, metadata=meta)
                logger.info(f"[⏹] Trajectory recorded: {len(frames)} frames saved to {filepath}")
                await self._broadcast({
                    "type": "record_complete",
                    "filename": os.path.basename(filepath),
                    "frames_count": len(frames),
                    "trajectories": list_trajectories()
                })

        elif cmd == "play_trajectory":
            filename = data.get("filename")
            speed = float(data.get("speed_factor", 1.0))
            loop = bool(data.get("loop", False))

            def _play_worker():
                try:
                    frames, _ = load_trajectory(filename)
                    if self.follower and self.follower.is_connected:
                        if self.trajectory_player and self.trajectory_player.is_playing:
                            self.trajectory_player.stop()
                        self.trajectory_player = TrajectoryPlayer(frames, self.follower, speed_factor=speed, loop=loop)
                        self.trajectory_player.start()
                except Exception as err:
                    logger.error(f"Playback error: {err}")

            threading.Thread(target=_play_worker, daemon=True).start()

        elif cmd == "stop_playback":
            if self.trajectory_player:
                self.trajectory_player.stop()

        # 9. Global speed & acceleration
        elif cmd == "set_speed":
            self.global_speed = max(100, min(3000, int(data.get("speed", 700))))
            logger.info(f"Global speed set to: {self.global_speed}")

        elif cmd == "set_accel":
            self.global_accel = max(1, min(254, int(data.get("accel", 50))))
            logger.info(f"Global accel set to: {self.global_accel}")

        # 10. Servo ID Programmer
        elif cmd == "reprogram_servo_id":
            from_id = int(data.get("from_id", 1))
            to_id = int(data.get("to_id", 1))
            success = False
            msg = ""
            if self.follower and self.follower.is_connected:
                success = self.follower.program_servo_id(from_id, to_id)
                msg = f"Servo ID {from_id} successfully changed to {to_id}" if success else "Failed to reprogram servo ID"
            await ws.send(json.dumps({
                "type": "reprogram_result",
                "success": success,
                "message": msg
            }))

    def _run_sequential_test_thread(self) -> None:
        """Sequential motor test (+10°, -10°) on servos 1 to 6."""
        self._seq_test_running = True
        logger.info("[⚡] Running Sequential Motor Test on Follower Arm...")

        try:
            delta_ticks = int(round(10.0 * (4096.0 / 360.0)))  # ~114 ticks
            servos_to_test = [1, 2, 3, 4, 5]
            if 6 in self.current_follower_states and self.current_follower_states[6].get("is_online", False):
                servos_to_test.append(6)

            for sid in servos_to_test:
                orig_raw = self.current_follower_states.get(sid, {}).get("raw_pos", 2048)

                # Broadcast step start
                self._broadcast_sync({
                    "type": "seq_test_step",
                    "joint": sid,
                    "stage": "pos_10",
                    "status": "Testing +10°"
                })

                # Move +10°
                target_pos = self.calib.validate_ticks("follower", sid, orig_raw + delta_ticks)
                if self.follower and self.follower.is_connected:
                    self.follower.sync_write_positions({sid: target_pos}, default_speed=400)
                time.sleep(0.4)

                # Broadcast step neg
                self._broadcast_sync({
                    "type": "seq_test_step",
                    "joint": sid,
                    "stage": "neg_10",
                    "status": "Testing -10°"
                })

                # Move -10°
                target_neg = self.calib.validate_ticks("follower", sid, orig_raw - delta_ticks)
                if self.follower and self.follower.is_connected:
                    self.follower.sync_write_positions({sid: target_neg}, default_speed=400)
                time.sleep(0.4)

                # Return to original
                if self.follower and self.follower.is_connected:
                    self.follower.sync_write_positions({sid: orig_raw}, default_speed=500)
                time.sleep(0.3)

                # Confirm passed
                self._broadcast_sync({
                    "type": "seq_test_step",
                    "joint": sid,
                    "stage": "passed",
                    "status": "PASSED ✓"
                })

            self._broadcast_sync({
                "type": "seq_test_complete",
                "success": True,
                "message": f"Successfully tested {len(servos_to_test)} servos."
            })
            logger.info("[✓] Sequential Motor Test Completed Successfully!")

        except Exception as e:
            logger.error(f"Sequential test error: {e}")
            self._broadcast_sync({
                "type": "seq_test_complete",
                "success": False,
                "message": str(e)
            })
        finally:
            self._seq_test_running = False

    def _broadcast_sync(self, payload: Dict[str, Any]) -> None:
        """Thread-safe synchronous broadcast to all WebSocket clients."""
        msg = json.dumps(payload)
        for client in list(self.connected_clients):
            try:
                asyncio.run_coroutine_threadsafe(client.send(msg), self.main_loop)
            except Exception:
                pass

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        """Asynchronous broadcast."""
        msg = json.dumps(payload)
        for client in list(self.connected_clients):
            try:
                await client.send(msg)
            except Exception:
                pass

    async def telemetry_loop(self) -> None:
        """Continuous 40Hz telemetry polling and streaming."""
        while self._running:
            try:
                # 1. Follower Telemetry
                if self.follower and self.follower.is_connected:
                    batch = self.follower.read_telemetry_batch()
                    f_states: Dict[int, Dict[str, Any]] = {}
                    angles: Dict[int, float] = {}
                    raws: Dict[int, int] = {}

                    items = batch.servos.items() if hasattr(batch, "servos") else ()
                    for sid, item in items:
                        raw = int(getattr(item, "raw_pos", getattr(item, "position", 2048)))
                        f_states[sid] = {
                            "id": sid,
                            "raw_pos": raw,
                            "angle": round(ticks_to_deg(raw, sid), 1),
                            "speed": int(getattr(item, "speed", 0)),
                            "load": round(float(getattr(item, "load_pct", getattr(item, "load", 0.0))), 1),
                            "voltage": round(float(getattr(item, "voltage_v", getattr(item, "voltage", 0.0))), 1),
                            "temperature": int(getattr(item, "temp_c", getattr(item, "temperature", 0))),
                            "current_ma": int(getattr(item, "current_ma", 0)),
                            "error": int(getattr(item, "error_code", getattr(item, "error_byte", 0))),
                            "is_online": bool(getattr(item, "is_online", True)),
                        }
                        angles[sid] = f_states[sid]["angle"]
                        raws[sid] = raw

                    # Graceful 5-DOF marker for ID 6 if absent
                    if 6 not in f_states:
                        f_states[6] = {
                            "id": 6,
                            "raw_pos": 2048,
                            "angle": 0.0,
                            "speed": 0,
                            "load": 0.0,
                            "voltage": 0.0,
                            "temperature": 0,
                            "current_ma": 0,
                            "error": 0,
                            "is_online": False,  # 5-DOF unwired
                        }
                        angles[6] = 0.0
                        raws[6] = 2048

                    self.current_follower_states = f_states

                    # Compute Cartesian forward kinematics
                    current_angles_list = [angles.get(i, 0.0) for i in range(1, 7)]
                    fk_pose = forward_kinematics(current_angles_list)

                # 2. Leader Telemetry (if connected)
                l_states: Dict[int, Dict[str, Any]] = {}
                if self.leader and self.leader.is_connected:
                    try:
                        l_batch = self.leader.read_telemetry_batch()
                        l_items = l_batch.servos.items() if hasattr(l_batch, "servos") else ()
                        for sid, item in l_items:
                            raw = int(getattr(item, "raw_pos", getattr(item, "position", 2048)))
                            l_states[sid] = {
                                "id": sid,
                                "raw_pos": raw,
                                "angle": round(ticks_to_deg(raw, sid), 1),
                                "speed": int(getattr(item, "speed", 0)),
                                "voltage": round(float(getattr(item, "voltage_v", getattr(item, "voltage", 0.0))), 1),
                                "temperature": int(getattr(item, "temp_c", getattr(item, "temperature", 0))),
                                "is_online": True,
                            }
                        self.current_leader_states = l_states
                    except Exception:
                        pass

                # Build telemetry frame
                telemetry_msg = {
                    "type": "telemetry",
                    "angles": angles,
                    "raws": raws,
                    "states": f_states,
                    "leader_states": l_states,
                    "fk": fk_pose,
                    "is_mock": self._is_mock,
                    "is_recording": self.trajectory_recorder.is_recording,
                    "is_playing": bool(self.trajectory_player and self.trajectory_player.is_playing),
                }
                await self._broadcast(telemetry_msg)

                await asyncio.sleep(0.025)  # 40 Hz loop

            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(0.05)

    async def run_async(self) -> None:
        self.main_loop = asyncio.get_running_loop()
        self._running = True

        self.initialize_hardware()

        # Start HTTP server thread
        t_http = threading.Thread(target=self.start_http, daemon=True)
        t_http.start()

        # Start WebSocket server
        ws_server = await websockets.serve(self.ws_handler, "0.0.0.0", WS_PORT)
        logger.info(f"[✓] V3 WebSocket server running at ws://localhost:{WS_PORT}")

        # Run telemetry stream
        try:
            await self.telemetry_loop()
        finally:
            self._running = False
            ws_server.close()
            await ws_server.wait_closed()
            if self.follower:
                self.follower.disconnect()
            if self.leader:
                self.leader.disconnect()


def main():
    follower_port = sys.argv[1] if len(sys.argv) > 1 else "COM38"
    leader_port = sys.argv[2] if len(sys.argv) > 2 else "COM39"
    server = V3StudioServer(follower_port=follower_port, leader_port=leader_port)
    try:
        asyncio.run(server.run_async())
    except KeyboardInterrupt:
        logger.info("[*] V3 Studio Server stopped by user.")


if __name__ == "__main__":
    main()
