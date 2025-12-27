"""Performance monitoring tools for Android UI Agent.

Provides CPU, memory, network, and FPS monitoring for apps.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core import DeviceConnectionError, get_device_manager

logger = logging.getLogger(__name__)

# Security: Max sessions to prevent unbounded memory growth
MAX_MONITORING_SESSIONS = 10
# Security: Max snapshots per session to limit memory
MAX_SNAPSHOTS_PER_SESSION = 1000
_MAX_PACKAGE_NAME_LENGTH = 256
_PACKAGE_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$")
_CPU_MEM_RE = re.compile(r"(\d+\.?\d*)\s+(\d+\.?\d*)\s+\d+:\d+\.\d+\s+")
_MEMINFO_TOTAL_RE = re.compile(r"TOTAL:\s+(\d+)")
_BATTERY_LEVEL_RE = re.compile(r"level:\s*(\d+)")
_BATTERY_TEMP_RE = re.compile(r"temperature:\s*(\d+)")


def _validate_package_name(package: str) -> bool:
    """Validate Android package name to prevent command injection.

    Valid package names:
    - Contain only alphanumeric characters, underscores, and dots
    - Must start with a letter
    - Each segment must start with a letter

    Args:
        package: Package name to validate

    Returns:
        True if valid, False otherwise
    """
    if not package:
        return False
    # Android package names: letters, numbers, underscores, dots
    # Must start with letter, each segment after dot must start with letter
    return bool(_PACKAGE_RE.match(package)) and len(package) <= _MAX_PACKAGE_NAME_LENGTH


def _populate_cpu_memory(
    snapshot: PerformanceSnapshot,
    device,
    package: Optional[str],
) -> None:
    """Populate CPU and memory metrics for a package."""
    if not package:
        return

    valid_package = _validate_package_name(package)
    if not valid_package:
        logger.warning(f"Invalid package name rejected: {package[:50]}")
        return

    try:
        output = device.shell(f"top -n 1 -b | grep -F '{package}'")
        match = _CPU_MEM_RE.search(output)
        if match:
            snapshot.cpu_percent = float(match.group(1))
            snapshot.memory_percent = float(match.group(2))
    except Exception as e:
        logger.debug(f"Failed to get CPU metrics: {e}")

    try:
        output = device.shell(f"dumpsys meminfo '{package}' | head -20")
        match = _MEMINFO_TOTAL_RE.search(output)
        if match:
            snapshot.memory_mb = float(match.group(1)) / 1024  # KB to MB
    except Exception as e:
        logger.debug(f"Failed to get memory metrics: {e}")


def _populate_battery(snapshot: PerformanceSnapshot, device) -> None:
    """Populate battery metrics for device."""
    try:
        output = device.shell("dumpsys battery")
        level_match = _BATTERY_LEVEL_RE.search(output)
        temp_match = _BATTERY_TEMP_RE.search(output)
        if level_match:
            snapshot.battery_level = int(level_match.group(1))
        if temp_match:
            snapshot.battery_temperature = int(temp_match.group(1)) / 10.0
    except Exception:
        pass


def _populate_network(snapshot: PerformanceSnapshot, device) -> None:
    """Populate network metrics for device."""
    try:
        output = device.shell("cat /proc/net/dev")
        rx_total = 0
        tx_total = 0
        for line in output.split("\n"):
            if ":" in line and "lo:" not in line:
                parts = line.split()
                if len(parts) >= 10:
                    rx_total += int(parts[1])
                    tx_total += int(parts[9])
        snapshot.network_rx_bytes = rx_total
        snapshot.network_tx_bytes = tx_total
    except Exception:
        pass


def _populate_fps(snapshot: PerformanceSnapshot, device) -> None:
    """Populate FPS metrics for device."""
    try:
        device.shell("dumpsys SurfaceFlinger --latency-clear")
        time.sleep(0.5)
        output = device.shell("dumpsys SurfaceFlinger --latency SurfaceView")
        lines = [line for line in output.strip().split("\n") if line.strip()]
        if len(lines) > 2:
            valid_frames = sum(1 for line in lines[1:] if line.split()[0] != "0")
            snapshot.fps = valid_frames * 2  # Approximate FPS
    except Exception:
        pass


@dataclass
class PerformanceSnapshot:
    """A snapshot of performance metrics."""

    timestamp: float
    cpu_percent: Optional[float] = None
    memory_mb: Optional[float] = None
    memory_percent: Optional[float] = None
    fps: Optional[float] = None
    network_rx_bytes: Optional[int] = None
    network_tx_bytes: Optional[int] = None
    battery_level: Optional[int] = None
    battery_temperature: Optional[float] = None


@dataclass
class MonitoringSession:
    """A performance monitoring session."""

    session_id: str
    device_id: str
    package: str
    start_time: float
    snapshots: List[PerformanceSnapshot] = field(default_factory=list)
    is_running: bool = False


class PerformanceMonitor:
    """Monitors app performance metrics."""

    def __init__(self):
        self._sessions: Dict[str, MonitoringSession] = {}
        self._running: Dict[str, bool] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._poll_interval = 1.0

    def get_metrics_snapshot(
        self,
        device_id: str,
        package: Optional[str] = None,
    ) -> PerformanceSnapshot:
        """Get a single performance metrics snapshot.

        Args:
            device_id: Device identifier
            package: App package to monitor (None for overall)

        Returns:
            PerformanceSnapshot with current metrics
        """
        device_manager = get_device_manager()
        snapshot = PerformanceSnapshot(timestamp=time.time())

        try:
            with device_manager.get_device(device_id) as device:
                if not package:
                    current = device.app_current()
                    package = current.get("package")

                _populate_cpu_memory(snapshot, device, package)
                _populate_battery(snapshot, device)
                _populate_network(snapshot, device)
                _populate_fps(snapshot, device)

        except DeviceConnectionError:
            raise
        except Exception as e:
            logger.warning(f"Error collecting metrics: {e}")

        return snapshot

    def _monitor_loop(
        self,
        session_id: str,
        device_id: str,
        package: str,
    ):
        """Background monitoring loop."""
        logger.info(f"Monitoring started for session '{session_id}'")

        while self._running.get(session_id, False):
            try:
                snapshot = self.get_metrics_snapshot(device_id, package)

                with self._lock:
                    session = self._sessions.get(session_id)
                    if session:
                        # Limit snapshots per session to prevent memory overflow
                        if len(session.snapshots) >= MAX_SNAPSHOTS_PER_SESSION:
                            # Keep last 75% of snapshots
                            keep_count = int(MAX_SNAPSHOTS_PER_SESSION * 0.75)
                            session.snapshots = session.snapshots[-keep_count:]
                        session.snapshots.append(snapshot)

            except Exception as e:
                logger.warning(f"Monitoring error: {e}")

            time.sleep(self._poll_interval)

        logger.info(f"Monitoring stopped for session '{session_id}'")

    def start_monitoring(
        self,
        device_id: str,
        package: Optional[str] = None,
        poll_interval: float = 1.0,
    ) -> MonitoringSession:
        """Start background performance monitoring.

        Args:
            device_id: Device identifier
            package: App to monitor (None for current)
            poll_interval: Seconds between measurements

        Returns:
            MonitoringSession
        """
        import uuid

        device_manager = get_device_manager()

        # Get current package if not specified
        if not package:
            with device_manager.get_device(device_id) as device:
                current = device.app_current()
                package = current.get("package", "unknown")

        session_id = f"perf_{uuid.uuid4().hex[:8]}"
        session = MonitoringSession(
            session_id=session_id,
            device_id=device_id,
            package=package,
            start_time=time.time(),
            is_running=True,
        )

        with self._lock:
            # Limit total sessions to prevent unbounded memory growth
            if len(self._sessions) >= MAX_MONITORING_SESSIONS:
                # Remove oldest completed sessions
                completed = [
                    sid for sid, sess in self._sessions.items()
                    if not sess.is_running
                ]
                for sid in completed[:len(self._sessions) - MAX_MONITORING_SESSIONS + 1]:
                    self._sessions.pop(sid, None)
                    self._running.pop(sid, None)
                    self._threads.pop(sid, None)

            self._sessions[session_id] = session
            self._running[session_id] = True
            self._poll_interval = poll_interval

        thread = threading.Thread(
            target=self._monitor_loop,
            args=(session_id, device_id, package),
            daemon=True,
            name=f"perf-{session_id}",
        )
        self._threads[session_id] = thread
        thread.start()

        return session

    def stop_monitoring(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Stop monitoring and get summary.

        Args:
            session_id: Session to stop

        Returns:
            Summary dictionary
        """
        with self._lock:
            self._running[session_id] = False
            session = self._sessions.get(session_id)
            if session:
                session.is_running = False

        # Wait for thread
        thread = self._threads.pop(session_id, None)
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        if not session:
            return None

        # Calculate summary
        snapshots = session.snapshots
        if not snapshots:
            return {
                "session_id": session_id,
                "duration": time.time() - session.start_time,
                "sample_count": 0,
            }

        # Aggregate metrics
        cpu_values = [s.cpu_percent for s in snapshots if s.cpu_percent is not None]
        mem_values = [s.memory_mb for s in snapshots if s.memory_mb is not None]
        fps_values = [s.fps for s in snapshots if s.fps is not None]

        summary = {
            "session_id": session_id,
            "package": session.package,
            "duration": time.time() - session.start_time,
            "sample_count": len(snapshots),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else None,
                "max": max(cpu_values) if cpu_values else None,
                "min": min(cpu_values) if cpu_values else None,
            },
            "memory_mb": {
                "avg": sum(mem_values) / len(mem_values) if mem_values else None,
                "max": max(mem_values) if mem_values else None,
                "min": min(mem_values) if mem_values else None,
            },
            "fps": {
                "avg": sum(fps_values) / len(fps_values) if fps_values else None,
                "max": max(fps_values) if fps_values else None,
                "min": min(fps_values) if fps_values else None,
            },
        }

        return summary

    def get_session(self, session_id: str) -> Optional[MonitoringSession]:
        """Get a monitoring session."""
        with self._lock:
            return self._sessions.get(session_id)


# Global singleton
_performance_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global PerformanceMonitor instance."""
    global _performance_monitor
    with _monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
        return _performance_monitor


# === MCP Tool Functions ===


def get_performance_metrics(
    device_id: Optional[str] = None,
    package: Optional[str] = None,
) -> Dict[str, Any]:
    """Get current performance metrics snapshot.

    Args:
        device_id: Device serial (None for default)
        package: App package (None for current app)

    Returns:
        Dictionary with performance metrics:
        - cpu_percent: CPU usage
        - memory_mb: Memory usage in MB
        - memory_percent: Memory usage percentage
        - fps: Frames per second (approximate)
        - battery_level: Battery percentage
        - battery_temperature: Battery temperature
        - network_rx_bytes: Network bytes received
        - network_tx_bytes: Network bytes sent
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    monitor = get_performance_monitor()
    snapshot = monitor.get_metrics_snapshot(resolved_id, package)

    return {
        "timestamp": snapshot.timestamp,
        "cpu_percent": snapshot.cpu_percent,
        "memory_mb": snapshot.memory_mb,
        "memory_percent": snapshot.memory_percent,
        "fps": snapshot.fps,
        "battery": {
            "level": snapshot.battery_level,
            "temperature": snapshot.battery_temperature,
        },
        "network": {
            "rx_bytes": snapshot.network_rx_bytes,
            "tx_bytes": snapshot.network_tx_bytes,
        },
    }


def start_performance_monitor(
    device_id: Optional[str] = None,
    package: Optional[str] = None,
    poll_interval: float = 1.0,
) -> Dict[str, Any]:
    """Start background performance monitoring.

    Args:
        device_id: Device serial (None for default)
        package: App package (None for current app)
        poll_interval: Seconds between measurements

    Returns:
        Dictionary with session info
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    monitor = get_performance_monitor()
    session = monitor.start_monitoring(resolved_id, package, poll_interval)

    return {
        "success": True,
        "session_id": session.session_id,
        "package": session.package,
        "poll_interval": poll_interval,
    }


def stop_performance_monitor(session_id: str) -> Dict[str, Any]:
    """Stop performance monitoring and get summary.

    Args:
        session_id: Session to stop

    Returns:
        Dictionary with performance summary
    """
    monitor = get_performance_monitor()
    summary = monitor.stop_monitoring(session_id)

    if not summary:
        return {
            "success": False,
            "error": "Session not found",
        }

    return {
        "success": True,
        **summary,
    }
