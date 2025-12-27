"""Navigation tools for Android UI Agent.

Provides app lifecycle and navigation control.
"""
import logging
import time
from typing import Any, Dict, Optional

from ..core import DeviceConnectionError, get_device_manager
from ._errors import wrap_tool_errors

logger = logging.getLogger(__name__)


def _press_simple(
    label: str,
    key: str,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Press a single key and return a standard success payload."""
    device_manager = get_device_manager()

    try:
        with device_manager.get_device(device_id) as device:
            device.press(key)

            logger.info(f"Pressed {label}")

            return {"success": True}

    except DeviceConnectionError:
        raise
    except Exception as e:
        logger.error(f"Failed to press {label}: {e}")
        raise RuntimeError(f"Failed to press {label}: {e}")


def _open_panel(
    label: str,
    open_fn,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Open a system panel and return a standard success payload."""
    device_manager = get_device_manager()

    try:
        with device_manager.get_device(device_id) as device:
            open_fn(device)

            logger.info(f"Opened {label}")

            return {"success": True}

    except DeviceConnectionError:
        raise
    except Exception as e:
        logger.error(f"Failed to open {label}: {e}")
        raise RuntimeError(f"Failed to open {label}: {e}")

@wrap_tool_errors(logger, "Failed to start app")
def app_start(
    package: str,
    activity: Optional[str] = None,
    device_id: Optional[str] = None,
    wait: bool = True,
    stop_first: bool = False,
) -> Dict[str, Any]:
    """Start an application.

    Args:
        package: App package name (e.g., "com.example.app")
        activity: Activity to launch (optional, uses default launcher)
        device_id: Device serial (None for default)
        wait: Wait for app to launch
        stop_first: Stop app before starting (ensures fresh start)

    Returns:
        Dictionary with:
        - success: True if app started
        - package: Package that was started
        - activity: Activity that was started

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        if stop_first:
            device.app_stop(package)
            time.sleep(0.5)

        if activity:
            device.app_start(package, activity, wait=wait)
        else:
            device.app_start(package, wait=wait)

        logger.info(f"Started app: {package}")

        return {
            "success": True,
            "package": package,
            "activity": activity,
        }


@wrap_tool_errors(logger, "Failed to stop app")
def app_stop(
    package: str,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Stop an application.

    Args:
        package: App package name
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        device.app_stop(package)

        logger.info(f"Stopped app: {package}")

        return {
            "success": True,
            "package": package,
        }


@wrap_tool_errors(logger, "Failed to get current app")
def app_current(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Get current foreground app information.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with:
        - package: Current app package
        - activity: Current activity

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        current = device.app_current()

        return {
            "package": current.get("package"),
            "activity": current.get("activity"),
        }


def go_back(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Press the back button.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    return _press_simple("back button", "back", device_id)


def go_home(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Press the home button.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    return _press_simple("home button", "home", device_id)


@wrap_tool_errors(logger, "Failed to press key")
def press_key(
    key: str,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Press a key on the device.

    Args:
        key: Key to press. Common keys:
            - "back", "home", "menu", "recent"
            - "volume_up", "volume_down", "volume_mute"
            - "power", "camera"
            - "enter", "delete", "search"
            - "up", "down", "left", "right", "center"
            - Numeric keycodes (e.g., "66" for Enter)
        device_id: Device serial (None for default)

    Returns:
        Dictionary with:
        - success: True if key was pressed
        - key: The key that was pressed

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        device.press(key)

        logger.info(f"Pressed key: {key}")

        return {
            "success": True,
            "key": key,
        }


def open_notification(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Open the notification panel.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    return _open_panel("notification panel", lambda dev: dev.open_notification(), device_id)


def open_quick_settings(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Open the quick settings panel.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    return _open_panel("quick settings", lambda dev: dev.open_quick_settings(), device_id)


@wrap_tool_errors(logger, "Failed to set orientation", pass_through=(ValueError,))
def set_orientation(
    orientation: str,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Set device screen orientation.

    Args:
        orientation: "natural", "left", "right", or "upsidedown"
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status and orientation

    Raises:
        ValueError: Invalid orientation value
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    valid_orientations = ["natural", "left", "right", "upsidedown"]
    if orientation.lower() not in valid_orientations:
        raise ValueError(
            f"Invalid orientation: {orientation}. "
            f"Must be one of: {valid_orientations}"
        )

    with device_manager.get_device(device_id) as device:
        device.set_orientation(orientation.lower())

        logger.info(f"Set orientation: {orientation}")

        return {
            "success": True,
            "orientation": orientation.lower(),
        }
