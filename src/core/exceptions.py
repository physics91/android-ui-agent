"""Custom exceptions for Android UI Agent MCP Server.

Exception Hierarchy:
    AndroidAgentError (base)
    ├── DeviceConnectionError
    │   ├── DeviceNotFoundError
    │   └── InvalidDeviceIdError
    ├── RefError
    │   ├── StaleRefError
    │   ├── RefNotFoundError
    │   └── ElementNotFoundError
    └── WatcherError
"""


class AndroidAgentError(Exception):
    """Base exception for Android UI Agent."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert exception to dict for MCP response."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# === Device Errors ===


class DeviceConnectionError(AndroidAgentError):
    """Failed to connect to Android device."""

    def __init__(self, device_id: str, reason: str = None):
        message = f"Failed to connect to device: {device_id}"
        if reason:
            message += f" ({reason})"
        super().__init__(message, {"device_id": device_id, "reason": reason})
        self.device_id = device_id


class DeviceNotFoundError(DeviceConnectionError):
    """Device not found or not connected."""

    def __init__(self, device_id: str = None):
        if device_id:
            message = f"Device not found: {device_id}"
        else:
            message = "No Android devices connected"
        super().__init__(device_id or "none", message)


class InvalidDeviceIdError(AndroidAgentError):
    """Invalid device ID format (potential command injection)."""

    def __init__(self, device_id: str):
        super().__init__(
            f"Invalid device_id format: {device_id}",
            {"device_id": device_id, "hint": "Device ID must match [a-zA-Z0-9._:-]+"},
        )
        self.device_id = device_id


# === Ref System Errors ===


class RefError(AndroidAgentError):
    """Base class for ref-related errors."""

    pass


class StaleRefError(RefError):
    """Ref is stale (snapshot too old)."""

    def __init__(self, ref: str, snapshot_age_seconds: float):
        super().__init__(
            f"Stale ref: {ref}. Snapshot is {snapshot_age_seconds:.1f}s old. Call device_snapshot() to refresh.",
            {"ref": ref, "snapshot_age_seconds": snapshot_age_seconds},
        )
        self.ref = ref
        self.snapshot_age_seconds = snapshot_age_seconds


class RefNotFoundError(RefError):
    """Ref not found in current snapshot."""

    def __init__(self, ref: str, available_refs: list = None):
        details = {"ref": ref}
        if available_refs:
            details["available_refs_sample"] = available_refs[:10]
        super().__init__(f"Ref not found: {ref}", details)
        self.ref = ref


class ElementNotFoundError(RefError):
    """Element matching criteria not found."""

    def __init__(self, criteria: dict):
        super().__init__(
            f"Element not found matching criteria: {criteria}",
            {"criteria": criteria},
        )
        self.criteria = criteria


# === Watcher Errors ===


class WatcherError(AndroidAgentError):
    """Watcher-related errors."""

    def __init__(self, message: str, watcher_id: str = None):
        details = {}
        if watcher_id:
            details["watcher_id"] = watcher_id
        super().__init__(message, details)
        self.watcher_id = watcher_id
