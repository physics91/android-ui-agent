"""Recording tools for Android UI Agent.

Provides gesture recording and playback functionality.
"""
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core import DeviceConnectionError, get_device_manager

logger = logging.getLogger(__name__)

# Memory management limits
MAX_RECORDINGS = 50
MAX_EVENTS_PER_RECORDING = 5000
MAX_PLAYBACK_TIME_SECONDS = 600  # 10 minutes


def _execute_event(
    device,
    event: "GestureEvent",
    screen_size: Optional[tuple[int, int]] = None,
) -> None:
    """Execute a single recorded event against the device."""
    params = (
        _apply_coordinate_space(event.params, screen_size)
        if screen_size is not None
        else event.params
    )
    if event.type == "tap":
        device.click(int(params.get("x", 0)), int(params.get("y", 0)))
    elif event.type == "double_tap":
        device.double_click(int(params.get("x", 0)), int(params.get("y", 0)))
    elif event.type == "long_press":
        duration = params.get("duration", 1.0)
        device.long_click(
            int(params.get("x", 0)),
            int(params.get("y", 0)),
            duration=duration,
        )
    elif event.type == "swipe":
        duration = params.get("duration", 0.5)
        device.swipe(
            int(params.get("start_x", 0)),
            int(params.get("start_y", 0)),
            int(params.get("end_x", 0)),
            int(params.get("end_y", 0)),
            duration=duration,
        )
    elif event.type == "type":
        device.send_keys(params.get("text", ""))
    elif event.type == "key":
        device.press(params.get("key", ""))

@dataclass
class GestureEvent:
    """A single gesture event."""

    type: str  # "tap", "swipe", "long_press", "double_tap", "type", "key"
    timestamp: float  # Relative time from recording start
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GestureRecording:
    """A recording of gesture events."""

    recording_id: str
    device_id: str
    start_time: float
    events: List[GestureEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_recording: bool = False


class RecordingManager:
    """Manages gesture recordings."""

    def __init__(self):
        self._recordings: Dict[str, GestureRecording] = {}
        self._active: Dict[str, str] = {}  # device_id -> recording_id
        self._lock = threading.Lock()

    def start_recording(
        self,
        device_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[GestureRecording]:
        """Start a new gesture recording.

        Args:
            device_id: Device identifier
            metadata: Optional metadata to attach

        Returns:
            New GestureRecording
        """
        with self._lock:
            # Limit total recordings to prevent unbounded memory growth
            if len(self._recordings) >= MAX_RECORDINGS:
                # Remove oldest completed recordings
                completed = [
                    (rid, rec) for rid, rec in self._recordings.items()
                    if not rec.is_recording
                ]
                # Sort by start_time (oldest first)
                completed.sort(key=lambda x: x[1].start_time)
                if completed:
                    # Remove oldest until under limit
                    for rid, _ in completed[:len(self._recordings) - MAX_RECORDINGS + 1]:
                        self._recordings.pop(rid, None)
                        logger.debug(f"Evicted old recording: {rid}")
                else:
                    logger.warning(
                        "Recording limit reached; no completed recordings to evict"
                    )
                    return None

            recording_id = f"rec_{uuid.uuid4().hex[:12]}"

            recording = GestureRecording(
                recording_id=recording_id,
                device_id=device_id,
                start_time=time.time(),
                metadata=metadata or {},
                is_recording=True,
            )

            self._recordings[recording_id] = recording
            self._active[device_id] = recording_id

        logger.info(f"Started recording '{recording_id}' for device '{device_id}'")
        return recording

    def add_event(
        self,
        recording_id: str,
        event_type: str,
        params: Dict[str, Any],
    ) -> bool:
        """Add an event to a recording.

        Args:
            recording_id: Recording to add to
            event_type: Type of gesture event
            params: Event parameters

        Returns:
            True if event was added
        """
        with self._lock:
            recording = self._recordings.get(recording_id)
            if not recording or not recording.is_recording:
                return False

            # Limit events per recording to prevent memory overflow
            if len(recording.events) >= MAX_EVENTS_PER_RECORDING:
                logger.warning(
                    f"Recording {recording_id} reached max events ({MAX_EVENTS_PER_RECORDING})"
                )
                return False

            event = GestureEvent(
                type=event_type,
                timestamp=time.time() - recording.start_time,
                params=params,
            )
            recording.events.append(event)

        logger.debug(f"Added {event_type} event to recording '{recording_id}'")
        return True

    def stop_recording(self, recording_id: str) -> Optional[GestureRecording]:
        """Stop a recording.

        Args:
            recording_id: Recording to stop

        Returns:
            The stopped recording
        """
        with self._lock:
            recording = self._recordings.get(recording_id)
            if not recording:
                return None

            recording.is_recording = False
            recording.metadata["duration"] = time.time() - recording.start_time
            recording.metadata["event_count"] = len(recording.events)

            # Remove from active
            if self._active.get(recording.device_id) == recording_id:
                del self._active[recording.device_id]

        logger.info(
            f"Stopped recording '{recording_id}' with {len(recording.events)} events"
        )
        return recording

    def get_recording(self, recording_id: str) -> Optional[GestureRecording]:
        """Get a recording by ID."""
        with self._lock:
            return self._recordings.get(recording_id)

    def get_active_recording(self, device_id: str) -> Optional[GestureRecording]:
        """Get active recording for a device."""
        with self._lock:
            recording_id = self._active.get(device_id)
            if recording_id:
                return self._recordings.get(recording_id)
        return None

    def list_recordings(self) -> List[Dict[str, Any]]:
        """List all recordings."""
        with self._lock:
            return [
                {
                    "recording_id": rec.recording_id,
                    "device_id": rec.device_id,
                    "event_count": len(rec.events),
                    "duration": rec.metadata.get("duration"),
                    "is_recording": rec.is_recording,
                }
                for rec in self._recordings.values()
            ]

    def delete_recording(self, recording_id: str) -> bool:
        """Delete a recording."""
        with self._lock:
            if recording_id in self._recordings:
                del self._recordings[recording_id]
                return True
        return False

    def export_recording(self, recording_id: str) -> Optional[str]:
        """Export recording to JSON string."""
        with self._lock:
            recording = self._recordings.get(recording_id)
            if not recording:
                return None

            data = {
                "recording_id": recording.recording_id,
                "device_id": recording.device_id,
                "metadata": recording.metadata,
                "events": [
                    {
                        "type": e.type,
                        "timestamp": e.timestamp,
                        "params": e.params,
                    }
                    for e in recording.events
                ],
            }
            return json.dumps(data, indent=2)

    def import_recording(self, json_data: str) -> Optional[GestureRecording]:
        """Import recording from JSON string."""
        try:
            data = json.loads(json_data)
            recording_id = data.get("recording_id") or f"rec_{uuid.uuid4().hex[:12]}"

            recording = GestureRecording(
                recording_id=recording_id,
                device_id=data.get("device_id", "unknown"),
                start_time=0,
                metadata=data.get("metadata", {}),
                is_recording=False,
            )

            for event_data in data.get("events", []):
                event = GestureEvent(
                    type=event_data["type"],
                    timestamp=event_data["timestamp"],
                    params=event_data.get("params", {}),
                )
                recording.events.append(event)

            with self._lock:
                self._recordings[recording_id] = recording

            return recording

        except Exception as e:
            logger.error(f"Failed to import recording: {e}")
            return None

    def play_recording(
        self,
        recording_id: str,
        device_id: Optional[str] = None,
        speed: float = 1.0,
    ) -> Dict[str, Any]:
        """Play back a recording.

        Args:
            recording_id: Recording to play
            device_id: Device to play on (default: original device)
            speed: Playback speed multiplier (> 0)

        Returns:
            Dictionary with playback results
        """
        if speed <= 0:
            raise ValueError("speed must be greater than 0")

        device_manager = get_device_manager()

        with self._lock:
            recording = self._recordings.get(recording_id)
            if not recording:
                raise ValueError(f"Recording not found: {recording_id}")

        if recording.events:
            estimated_duration = recording.events[-1].timestamp / speed
            if estimated_duration > MAX_PLAYBACK_TIME_SECONDS:
                raise ValueError(
                    "Playback exceeds max duration "
                    f"({estimated_duration:.1f}s > {MAX_PLAYBACK_TIME_SECONDS}s)"
                )

        target_device = device_id or recording.device_id
        events_played = 0
        errors = []

        try:
            with device_manager.get_device(target_device) as device:
                screen_size = device.window_size()
                last_timestamp = 0

                for event_index, event in enumerate(recording.events):
                    # Wait for correct timing
                    delay = (event.timestamp - last_timestamp) / speed
                    if delay > 0:
                        time.sleep(delay)
                    last_timestamp = event.timestamp

                    try:
                        _execute_event(device, event, screen_size=screen_size)

                        events_played += 1

                    except Exception as e:
                        errors.append({"event_index": event_index, "error": str(e)})

        except DeviceConnectionError:
            raise

        logger.info(
            f"Played recording '{recording_id}': {events_played}/{len(recording.events)} events"
        )

        return {
            "success": len(errors) == 0,
            "events_played": events_played,
            "total_events": len(recording.events),
            "errors": errors,
        }


# Global singleton
_recording_manager: Optional[RecordingManager] = None
_manager_lock = threading.Lock()


def get_recording_manager() -> RecordingManager:
    """Get the global RecordingManager instance."""
    global _recording_manager
    with _manager_lock:
        if _recording_manager is None:
            _recording_manager = RecordingManager()
        return _recording_manager


# === Helpers ===


def _build_gesture_params(
    event_type: str,
    *,
    x: Optional[float] = None,
    y: Optional[float] = None,
    end_x: Optional[float] = None,
    end_y: Optional[float] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
    duration: Optional[float] = None,
    coordinate_space: Optional[str] = None,
    normalized: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build parameter payload for a gesture event."""
    params: Dict[str, Any] = {}
    if x is not None:
        params["x"] = x
    if y is not None:
        params["y"] = y
    if end_x is not None:
        params["end_x"] = end_x
    if end_y is not None:
        params["end_y"] = end_y
    if text is not None:
        params["text"] = text
    if key is not None:
        params["key"] = key
    if duration is not None:
        params["duration"] = duration
    if coordinate_space is None:
        if normalized is True:
            coordinate_space = "normalized"
        elif normalized is False:
            coordinate_space = "absolute"
    if coordinate_space is not None:
        params["coordinate_space"] = coordinate_space

    if event_type == "swipe":
        params["start_x"] = params.pop("x", 0)
        params["start_y"] = params.pop("y", 0)

    return params


def _apply_coordinate_space(
    params: Dict[str, Any],
    screen_size: Optional[tuple[int, int]],
) -> Dict[str, Any]:
    """Scale normalized coordinates into absolute pixels and clamp to screen size."""
    if params.get("coordinate_space") != "normalized":
        return dict(params)
    if screen_size is None:
        return dict(params)

    width, height = screen_size

    def _scale(value: Any, size: int) -> int:
        if size <= 0:
            return 0
        try:
            scaled = int(round(float(value) * size))
        except (TypeError, ValueError):
            return 0
        return max(0, min(size - 1, scaled))

    scaled = dict(params)
    for key in ("x", "start_x", "end_x"):
        if key in scaled:
            scaled[key] = _scale(scaled[key], width)
    for key in ("y", "start_y", "end_y"):
        if key in scaled:
            scaled[key] = _scale(scaled[key], height)
    return scaled


# === MCP Tool Functions ===


def start_gesture_recording(
    device_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Start recording gestures.

    Args:
        device_id: Device serial (None for default)
        metadata: Optional metadata to attach

    Returns:
        Dictionary with recording info
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_recording_manager()
    recording = manager.start_recording(resolved_id, metadata)

    if recording is None:
        return {
            "success": False,
            "error": "Recording limit reached",
        }

    return {
        "success": True,
        "recording_id": recording.recording_id,
        "device_id": recording.device_id,
    }


def add_gesture_event(
    recording_id: str,
    event_type: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    end_x: Optional[float] = None,
    end_y: Optional[float] = None,
    text: Optional[str] = None,
    key: Optional[str] = None,
    duration: Optional[float] = None,
    coordinate_space: Optional[str] = None,
    normalized: Optional[bool] = None,
) -> Dict[str, Any]:
    """Add a gesture event to recording.

    Args:
        recording_id: Recording to add to
        event_type: "tap", "swipe", "long_press", "double_tap", "type", "key"
        x, y: Coordinates (normalized 0-1 or absolute pixels)
        end_x, end_y: End coordinates for swipe
        text: Text for type event
        key: Key name for key event
        duration: Duration for long_press or swipe
        coordinate_space: "absolute" (pixels) or "normalized" (0-1)
        normalized: Convenience flag; True maps to coordinate_space="normalized"

    Returns:
        Dictionary with success status
    """
    manager = get_recording_manager()

    params = _build_gesture_params(
        event_type,
        x=x,
        y=y,
        end_x=end_x,
        end_y=end_y,
        text=text,
        key=key,
        duration=duration,
        coordinate_space=coordinate_space,
        normalized=normalized,
    )

    added = manager.add_event(recording_id, event_type, params)

    return {
        "success": added,
        "event_type": event_type,
    }


def stop_gesture_recording(recording_id: str) -> Dict[str, Any]:
    """Stop a gesture recording.

    Args:
        recording_id: Recording to stop

    Returns:
        Dictionary with recording summary
    """
    manager = get_recording_manager()
    recording = manager.stop_recording(recording_id)

    if not recording:
        return {
            "success": False,
            "error": "Recording not found",
        }

    return {
        "success": True,
        "recording_id": recording.recording_id,
        "event_count": len(recording.events),
        "duration": recording.metadata.get("duration", 0),
    }


def play_gesture_recording(
    recording_id: str,
    device_id: Optional[str] = None,
    speed: float = 1.0,
) -> Dict[str, Any]:
    """Play back a recorded gesture sequence.

    Args:
        recording_id: Recording to play
        device_id: Target device (None for original)
        speed: Playback speed (1.0 = normal, > 0)

    Returns:
        Dictionary with playback results
    """
    manager = get_recording_manager()
    return manager.play_recording(recording_id, device_id, speed)


def list_gesture_recordings() -> Dict[str, Any]:
    """List all gesture recordings.

    Returns:
        Dictionary with recording list
    """
    manager = get_recording_manager()
    recordings = manager.list_recordings()

    return {
        "count": len(recordings),
        "recordings": recordings,
    }


def export_gesture_recording(recording_id: str) -> Dict[str, Any]:
    """Export a recording to JSON.

    Args:
        recording_id: Recording to export

    Returns:
        Dictionary with JSON data
    """
    manager = get_recording_manager()
    json_data = manager.export_recording(recording_id)

    if not json_data:
        return {
            "success": False,
            "error": "Recording not found",
        }

    return {
        "success": True,
        "recording_id": recording_id,
        "json": json_data,
    }


def import_gesture_recording(json_data: str) -> Dict[str, Any]:
    """Import a recording from JSON.

    Args:
        json_data: JSON string of recording

    Returns:
        Dictionary with imported recording info
    """
    manager = get_recording_manager()
    recording = manager.import_recording(json_data)

    if not recording:
        return {
            "success": False,
            "error": "Failed to parse recording JSON",
        }

    return {
        "success": True,
        "recording_id": recording.recording_id,
        "event_count": len(recording.events),
    }


def delete_gesture_recording(recording_id: str) -> Dict[str, Any]:
    """Delete a recording.

    Args:
        recording_id: Recording to delete

    Returns:
        Dictionary with success status
    """
    manager = get_recording_manager()
    deleted = manager.delete_recording(recording_id)

    return {
        "success": deleted,
        "recording_id": recording_id,
    }
