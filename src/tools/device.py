"""Device management tools for Android UI Agent.

Provides device listing, selection, and information retrieval.
"""
import logging
from typing import Any, Dict, Optional

from ..core import DeviceNotFoundError, InvalidDeviceIdError, get_device_manager
from ._errors import wrap_tool_errors

logger = logging.getLogger(__name__)


def device_list() -> Dict[str, Any]:
    """List all connected Android devices.

    Returns information about all devices connected via ADB,
    including their state and basic info.

    Returns:
        Dictionary containing:
        - count: Number of connected devices
        - devices: List of device info dictionaries
            - serial: Device serial number
            - state: "device", "offline", or "unauthorized"
            - model: Device model (if available)
            - product: Product name (if available)
            - available: True if device can be used
        - selected: Currently selected device (if any)

    Example:
        >>> result = device_list()
        >>> for device in result["devices"]:
        ...     if device["available"]:
        ...         print(f"{device['serial']}: {device['model']}")
    """
    device_manager = get_device_manager()

    devices = device_manager.list_devices()
    selected = device_manager.get_selected_device()

    device_list = [
        {
            "serial": d.serial,
            "state": d.state,
            "model": d.model,
            "product": d.product,
            "transport_id": d.transport_id,
            "available": d.is_available,
        }
        for d in devices
    ]

    available_count = sum(1 for d in devices if d.is_available)
    logger.info(f"Found {len(devices)} devices ({available_count} available)")

    return {
        "count": len(devices),
        "available_count": available_count,
        "devices": device_list,
        "selected": selected,
    }


@wrap_tool_errors(
    logger,
    "Device selection failed",
    pass_through=(InvalidDeviceIdError, DeviceNotFoundError),
)
def device_select(device_id: str) -> Dict[str, Any]:
    """Select a device as the default for subsequent operations.

    When multiple devices are connected, use this to specify which
    device should be used for operations that don't specify a device_id.

    Args:
        device_id: Device serial number to select

    Returns:
        Dictionary containing:
        - success: True if selection was successful
        - selected: The device ID that was selected
        - previous: The previously selected device (if any)

    Example:
        >>> # List devices
        >>> devices = device_list()
        >>> # Select specific device
        >>> device_select("emulator-5554")
        >>> # All subsequent operations use this device
        >>> device_snapshot()  # Uses emulator-5554

    Raises:
        InvalidDeviceIdError: Invalid device ID format
        DeviceNotFoundError: Device not found or not available
    """
    device_manager = get_device_manager()

    previous = device_manager.get_selected_device()
    device_manager.select_device(device_id)

    logger.info(f"Selected device: {device_id} (previous: {previous})")

    return {
        "success": True,
        "selected": device_id,
        "previous": previous,
    }


@wrap_tool_errors(logger, "Failed to get device info")
def device_info(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information about a device.

    Returns comprehensive device information including screen size,
    Android version, and current state.

    Args:
        device_id: Device serial (None for default/selected device)

    Returns:
        Dictionary containing:
        - serial: Device serial number
        - sdk_version: Android SDK version (e.g., 33)
        - android_version: Android version string (e.g., "13")
        - product_name: Product name
        - screen_size: {width, height} in pixels
        - display_density: Display density
        - orientation: Current orientation (0, 1, 2, 3)
        - screen_on: Whether screen is on
        - battery: Battery info (if available)
        - current_app: Current foreground app

    Raises:
        DeviceConnectionError: Failed to connect to device
        DeviceNotFoundError: No devices available
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        # Basic device info
        info = device.info
        window = device.window_size()

        # Current app
        current_app = device.app_current()

        # Try to get battery info
        battery = None
        try:
            battery_info = device.shell("dumpsys battery")
            level = None
            status = None
            for line in battery_info.split("\n"):
                if "level:" in line:
                    level = int(line.split(":")[1].strip())
                elif "status:" in line:
                    status = line.split(":")[1].strip()
            if level is not None:
                battery = {"level": level, "status": status}
        except Exception:
            pass

        result = {
            "serial": device.serial,
            "sdk_version": info.get("sdkInt"),
            "android_version": info.get("platformVersion"),
            "product_name": info.get("productName"),
            "screen_size": {"width": window[0], "height": window[1]},
            "display_density": info.get("displaySizeDpX"),
            "orientation": info.get("displayRotation"),
            "screen_on": info.get("screenOn"),
            "battery": battery,
            "current_app": {
                "package": current_app.get("package"),
                "activity": current_app.get("activity"),
            },
        }

        logger.info(f"Device info retrieved: {device.serial}")
        return result


@wrap_tool_errors(logger, "Device unlock failed")
def device_unlock(
    device_id: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """Unlock the device screen.

    Wakes up the device and attempts to unlock it. If password is
    provided, it will be entered after swiping to unlock.

    Args:
        device_id: Device serial (None for default/selected device)
        password: Screen lock password/PIN (optional)

    Returns:
        Dictionary containing:
        - success: True if unlock was attempted
        - screen_was_off: Whether screen was off before
        - password_entered: Whether password was entered

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        # Check screen state
        info = device.info
        screen_was_off = not info.get("screenOn", True)

        # Wake up screen
        if screen_was_off:
            device.press("power")

        # Unlock (swipe up)
        device.unlock()

        # Enter password if provided
        password_entered = False
        if password:
            # Security: Never log password value
            device.send_keys(password)
            device.press("enter")
            password_entered = True

        # Security: Only log that password was used, not the value
        logger.info(
            "Device unlock attempted "
            f"(screen was off: {screen_was_off}, password_used: {password_entered})"
        )

        return {
            "success": True,
            "screen_was_off": screen_was_off,
            "password_entered": password_entered,
        }
