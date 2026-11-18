"""
Safe, Asynchronous Logging Module for SO-101 Robotics Studio V4.
Provides non-blocking logging with file persistence, console output, and GUI subscriber callbacks.
"""

from __future__ import annotations

import atexit
import logging
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional


class StudioLogger:
    """Thread-safe, asynchronous logger designed for high-frequency robotics studios."""

    _instance: Optional[StudioLogger] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> StudioLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, log_file: Optional[Path | str] = None, level: int = logging.INFO):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self.level = level
        self._queue: queue.Queue[Optional[tuple[str, int, str]]] = queue.Queue(maxsize=10000)
        self._subscribers: List[Callable[[str, int, str], None]] = []
        self._subscribers_lock = threading.Lock()

        # Determine log file path
        if log_file is None:
            base_dir = Path(__file__).resolve().parents[1]
            self.log_file = base_dir / "v4_studio.log"
        else:
            self.log_file = Path(log_file)

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._log_worker,
            name="StudioLoggerWorker",
            daemon=True,
        )
        self._worker_thread.start()
        atexit.register(self.shutdown)

    def _format_record(self, timestamp: float, level_name: str, message: str) -> str:
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        return f"{time_str} [{level_name:<7}] {message}"

    def _log_worker(self) -> None:
        """Background worker thread draining log queue to file, console, and listeners."""
        file_handle = None
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handle = open(self.log_file, "a", encoding="utf-8", buffering=1)
        except Exception as e:
            sys.stderr.write(f"[StudioLogger] Could not open log file {self.log_file}: {e}\n")

        while self._running or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            level_name, level_no, message = item
            timestamp = time.time()
            formatted = self._format_record(timestamp, level_name, message)

            # 1. Console Output
            if level_no >= logging.ERROR:
                sys.stderr.write(formatted + "\n")
                sys.stderr.flush()
            else:
                sys.stdout.write(formatted + "\n")
                sys.stdout.flush()

            # 2. File Output
            if file_handle:
                try:
                    file_handle.write(formatted + "\n")
                except Exception:
                    pass

            # 3. Notify Subscribers (e.g. GUI widgets)
            with self._subscribers_lock:
                active_subs = list(self._subscribers)

            for sub in active_subs:
                try:
                    sub(level_name, level_no, formatted)
                except Exception:
                    # Never crash the logger on faulty subscriber callback
                    pass

            self._queue.task_done()

        if file_handle:
            try:
                file_handle.flush()
                file_handle.close()
            except Exception:
                pass

    def log(self, level: int, message: str) -> None:
        if level < self.level:
            return

        level_name = logging.getLevelName(level)
        try:
            self._queue.put_nowait((level_name, level, str(message)))
        except queue.Full:
            # Under extreme load, drop silently or print emergency alert to avoid stalling control thread
            pass

    def debug(self, msg: str) -> None:
        self.log(logging.DEBUG, msg)

    def info(self, msg: str) -> None:
        self.log(logging.INFO, msg)

    def warning(self, msg: str) -> None:
        self.log(logging.WARNING, msg)

    def error(self, msg: str) -> None:
        self.log(logging.ERROR, msg)

    def critical(self, msg: str) -> None:
        self.log(logging.CRITICAL, msg)

    def subscribe(self, callback: Callable[[str, int, str], None]) -> None:
        """Register a callback (level_name, level_no, formatted_msg) to receive log events."""
        with self._subscribers_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, int, str], None]) -> None:
        """Unregister a previously registered log subscriber callback."""
        with self._subscribers_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def shutdown(self) -> None:
        """Flushes remaining records and gracefully terminates worker thread."""
        if not self._running:
            return
        self._running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        if threading.current_thread() != self._worker_thread:
            self._worker_thread.join(timeout=1.0)


def get_logger(name: str = "StudioLogger") -> StudioLogger:
    """Helper to retrieve the singleton studio logger instance."""
    return StudioLogger()
