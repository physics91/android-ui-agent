"""Wait tools for Android UI Agent.

Provides various wait conditions for synchronization.
"""
import logging
import time
from typing import Any, Dict, Optional

from ..core import get_device_manager, get_snapshot_manager
from .snapshot import _capture_snapshot
from ._errors import wrap_tool_errors

logger = logging.getLogger(__name__)


def _build_element_criteria(
    text: Optional[str] = None,
    text_contains: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_id_contains: Optional[str] = None,
    class_name: Optional[str] = None,
    content_desc: Optional[str] = None,
) -> Dict[str, Any]:
    """Build criteria dict for element matching."""
    criteria: Dict[str, Any] = {}
    if text is not None:
        criteria["text"] = text
    if text_contains is not None:
        criteria["text_contains"] = text_contains
    if resource_id is not None:
        criteria["resource_id"] = resource_id
    if resource_id_contains is not None:
        criteria["resource_id_contains"] = resource_id_contains
    if class_name is not None:
        criteria["class_name"] = class_name
    if content_desc is not None:
        criteria["content_desc"] = content_desc
    return criteria


def _validate_polling(timeout: float, poll_interval: float) -> None:
    """Validate polling configuration."""
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0")
    if poll_interval <= 0:
        raise ValueError("poll_interval must be greater than 0")


def _poll_until(
    timeout: float,
    poll_interval: float,
    check,
) -> tuple[bool, Any, float]:
    """Poll until check returns a non-None result or timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = check()
        if result is not None:
            return True, result, time.time() - start_time
        time.sleep(poll_interval)
    return False, None, time.time() - start_time


def wait(
    seconds: float,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Wait for a specified duration.

    Simple wait function for timing between actions.

    Args:
        seconds: Duration to wait in seconds
        device_id: Device serial (ignored, for consistency)

    Returns:
        Dictionary with:
        - success: True
        - waited: Actual seconds waited
    """
    time.sleep(seconds)
    logger.info(f"Waited {seconds} seconds")

    return {
        "success": True,
        "waited": seconds,
    }


@wrap_tool_errors(logger, "Wait for element failed", pass_through=(ValueError,))
def wait_for_element(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    text_contains: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_id_contains: Optional[str] = None,
    class_name: Optional[str] = None,
    content_desc: Optional[str] = None,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    """Wait for an element to appear.

    Repeatedly takes snapshots until element is found or timeout.

    Args:
        device_id: Device serial (None for default)
        text: Exact text match
        text_contains: Partial text match
        resource_id: Exact resource ID
        resource_id_contains: Partial resource ID
        class_name: Element class name
        content_desc: Content description
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks

    Returns:
        Dictionary with:
        - found: True if element was found
        - ref: Ref ID of found element (first match)
        - element: Element info
        - waited: Seconds waited

    Raises:
        DeviceConnectionError: Failed to connect to device
        ValueError: Invalid timeout or poll_interval
    """
    device_manager = get_device_manager()
    snapshot_manager = get_snapshot_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)
    _validate_polling(timeout, poll_interval)

    criteria = _build_element_criteria(
        text=text,
        text_contains=text_contains,
        resource_id=resource_id,
        resource_id_contains=resource_id_contains,
        class_name=class_name,
        content_desc=content_desc,
    )

    def check():
        _capture_snapshot(device_id)
        matches = snapshot_manager.find_elements(resolved_id, **criteria)
        return matches[0] if matches else None

    found, element, waited = _poll_until(timeout, poll_interval, check)
    if found and element is not None:
        logger.info(
            f"Element found after {waited:.2f}s: ref={element.ref}"
        )
        return {
            "found": True,
            "ref": element.ref,
            "element": element.to_dict(),
            "waited": waited,
        }

    logger.info(f"Element not found after {waited:.2f}s timeout")
    return {
        "found": False,
        "ref": None,
        "element": None,
        "waited": waited,
    }


def wait_for_text(
    text: str,
    device_id: Optional[str] = None,
    partial: bool = False,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    """Wait for text to appear on screen.

    Convenience wrapper around wait_for_element for text search.

    Args:
        text: Text to wait for
        device_id: Device serial (None for default)
        partial: If True, match partial text
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks

    Returns:
        Dictionary with found status and element info
    """
    if partial:
        return wait_for_element(
            device_id=device_id,
            text_contains=text,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    else:
        return wait_for_element(
            device_id=device_id,
            text=text,
            timeout=timeout,
            poll_interval=poll_interval,
        )


@wrap_tool_errors(logger, "Wait for activity failed", pass_through=(ValueError,))
def wait_for_activity(
    activity: str,
    device_id: Optional[str] = None,
    package: Optional[str] = None,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    """Wait for a specific activity to become active.

    Args:
        activity: Activity name (can be partial, e.g., ".MainActivity")
        device_id: Device serial (None for default)
        package: Optional package filter
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks

    Returns:
        Dictionary with:
        - found: True if activity was found
        - package: Current package
        - activity: Current activity
        - waited: Seconds waited

    Raises:
        DeviceConnectionError: Failed to connect to device
        ValueError: Invalid timeout or poll_interval
    """
    device_manager = get_device_manager()
    _validate_polling(timeout, poll_interval)

    def check():
        with device_manager.get_device(device_id) as device:
            current = device.app_current()
            current_package = current.get("package", "")
            current_activity = current.get("activity", "")

            if package and package not in current_package:
                return None

            if activity in current_activity:
                return current_package, current_activity

        return None

    found, payload, waited = _poll_until(timeout, poll_interval, check)
    if found and payload is not None:
        current_package, current_activity = payload
        logger.info(
            f"Activity found after {waited:.2f}s: "
            f"{current_package}/{current_activity}"
        )
        return {
            "found": True,
            "package": current_package,
            "activity": current_activity,
            "waited": waited,
        }

    logger.info(f"Activity not found after {waited:.2f}s timeout")
    return {
        "found": False,
        "package": None,
        "activity": None,
        "waited": waited,
    }


@wrap_tool_errors(logger, "Wait for element gone failed", pass_through=(ValueError,))
def wait_for_element_gone(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    text_contains: Optional[str] = None,
    resource_id: Optional[str] = None,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> Dict[str, Any]:
    """Wait for an element to disappear.

    Args:
        device_id: Device serial (None for default)
        text: Exact text match
        text_contains: Partial text match
        resource_id: Exact resource ID
        timeout: Maximum wait time in seconds
        poll_interval: Time between checks

    Returns:
        Dictionary with:
        - gone: True if element disappeared
        - waited: Seconds waited

    Raises:
        DeviceConnectionError: Failed to connect to device
        ValueError: Invalid timeout or poll_interval
    """
    device_manager = get_device_manager()
    snapshot_manager = get_snapshot_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)
    _validate_polling(timeout, poll_interval)

    criteria = _build_element_criteria(
        text=text,
        text_contains=text_contains,
        resource_id=resource_id,
    )

    def check():
        _capture_snapshot(device_id)
        matches = snapshot_manager.find_elements(resolved_id, **criteria)
        return True if not matches else None

    found, _, waited = _poll_until(timeout, poll_interval, check)
    if found:
        logger.info(f"Element gone after {waited:.2f}s")
        return {
            "gone": True,
            "waited": waited,
        }

    logger.info(f"Element still present after {waited:.2f}s timeout")
    return {
        "gone": False,
        "waited": waited,
    }
