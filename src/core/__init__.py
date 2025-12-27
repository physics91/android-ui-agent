"""Core modules for Android UI Agent MCP Server."""
from .exceptions import (
    AndroidAgentError,
    DeviceConnectionError,
    DeviceNotFoundError,
    InvalidDeviceIdError,
    StaleRefError,
    RefNotFoundError,
    ElementNotFoundError,
    WatcherError,
)
from .ref_system import ElementInfo, Snapshot, SnapshotManager, get_snapshot_manager
from .device_manager import DeviceManager, DeviceInfo, get_device_manager, validate_device_id

__all__ = [
    # Exceptions
    "AndroidAgentError",
    "DeviceConnectionError",
    "DeviceNotFoundError",
    "InvalidDeviceIdError",
    "StaleRefError",
    "RefNotFoundError",
    "ElementNotFoundError",
    "WatcherError",
    # Ref System
    "ElementInfo",
    "Snapshot",
    "SnapshotManager",
    "get_snapshot_manager",
    # Device Manager
    "DeviceManager",
    "DeviceInfo",
    "get_device_manager",
    "validate_device_id",
]
