"""Interaction tools for Android UI Agent.

Provides UI interaction capabilities using Playwright-style ref system.
"""
import logging
import time
from typing import Any, Dict, Optional, Tuple

from ..core import RefNotFoundError, StaleRefError, get_device_manager, get_snapshot_manager
from ._errors import wrap_tool_errors

logger = logging.getLogger(__name__)


def _resolve_position(
    device_id: str,
    ref: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
) -> Tuple[int, int]:
    """Resolve position from ref or coordinates.

    Args:
        device_id: Device identifier
        ref: Element ref ID (e.g., "e5")
        x: X coordinate (alternative to ref)
        y: Y coordinate (alternative to ref)

    Returns:
        (x, y) tuple of coordinates

    Raises:
        ValueError: Neither ref nor coordinates provided
        RefNotFoundError: Ref not found in snapshot
        StaleRefError: Snapshot is too old
    """
    if ref is not None:
        snapshot_manager = get_snapshot_manager()
        return snapshot_manager.get_position(device_id, ref)
    elif x is not None and y is not None:
        return (x, y)
    else:
        raise ValueError("Either 'ref' or both 'x' and 'y' must be provided")


def _redact_text(text: str) -> str:
    """Return a safe description for logs without exposing content."""
    return f"<{len(text)} chars>"


def _describe_target(
    element: Optional[str],
    ref: Optional[str],
    pos: Optional[Tuple[int, int]] = None,
    default: str = "focused element",
) -> str:
    """Return a human-friendly target description for logs."""
    if element:
        return element
    if ref:
        return f"ref={ref}"
    if pos is not None:
        return f"({pos[0]}, {pos[1]})"
    return default


_INTERACTION_PASSTHROUGH = (ValueError, RefNotFoundError, StaleRefError)


@wrap_tool_errors(logger, "Tap failed", pass_through=_INTERACTION_PASSTHROUGH)
def device_tap(
    ref: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    device_id: Optional[str] = None,
    element: Optional[str] = None,
) -> Dict[str, Any]:
    """Tap on an element or coordinate.

    Uses ref from device_snapshot() for Playwright-style element targeting.
    Alternatively, can tap on specific coordinates.

    Args:
        ref: Element ref ID from snapshot (e.g., "e5")
        x: X coordinate (alternative to ref)
        y: Y coordinate (alternative to ref)
        device_id: Device serial (None for default/selected device)
        element: Human-readable element description (for logging only)

    Returns:
        Dictionary containing:
        - success: True if tap was successful
        - position: {x, y} coordinates tapped
        - element: Description of element tapped
        - ref: The ref used (if applicable)

    Example:
        >>> # Using ref from snapshot
        >>> snapshot = device_snapshot()
        >>> device_tap(ref="e5", element="Login button")

        >>> # Using coordinates
        >>> device_tap(x=500, y=300)

    Raises:
        ValueError: Neither ref nor coordinates provided
        RefNotFoundError: Ref not found in snapshot
        StaleRefError: Snapshot is too old (take new snapshot)
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    # Resolve position
    pos_x, pos_y = _resolve_position(resolved_id, ref, x, y)

    # Execute tap
    with device_manager.get_device(device_id) as device:
        device.click(pos_x, pos_y)

    description = _describe_target(element, ref, (pos_x, pos_y))
    logger.info(f"Tapped at ({pos_x}, {pos_y}): {description}")

    return {
        "success": True,
        "position": {"x": pos_x, "y": pos_y},
        "element": element,
        "ref": ref,
    }


@wrap_tool_errors(logger, "Double tap failed", pass_through=_INTERACTION_PASSTHROUGH)
def device_double_tap(
    ref: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    device_id: Optional[str] = None,
    element: Optional[str] = None,
    interval: float = 0.1,
) -> Dict[str, Any]:
    """Double tap on an element or coordinate.

    Args:
        ref: Element ref ID from snapshot (e.g., "e5")
        x: X coordinate (alternative to ref)
        y: Y coordinate (alternative to ref)
        device_id: Device serial (None for default/selected device)
        element: Human-readable element description
        interval: Time between taps in seconds

    Returns:
        Dictionary with success status and position info

    Raises:
        Same as device_tap
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    pos_x, pos_y = _resolve_position(resolved_id, ref, x, y)

    with device_manager.get_device(device_id) as device:
        device.double_click(pos_x, pos_y, duration=interval)

    description = _describe_target(element, ref, (pos_x, pos_y))
    logger.info(f"Double-tapped at ({pos_x}, {pos_y}): {description}")

    return {
        "success": True,
        "position": {"x": pos_x, "y": pos_y},
        "element": element,
        "ref": ref,
    }


@wrap_tool_errors(logger, "Long press failed", pass_through=_INTERACTION_PASSTHROUGH)
def device_long_press(
    ref: Optional[str] = None,
    x: Optional[int] = None,
    y: Optional[int] = None,
    device_id: Optional[str] = None,
    element: Optional[str] = None,
    duration: float = 1.0,
) -> Dict[str, Any]:
    """Long press on an element or coordinate.

    Args:
        ref: Element ref ID from snapshot
        x: X coordinate (alternative to ref)
        y: Y coordinate (alternative to ref)
        device_id: Device serial (None for default/selected device)
        element: Human-readable element description
        duration: Press duration in seconds (default 1.0)

    Returns:
        Dictionary with success status and position info

    Raises:
        Same as device_tap
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    pos_x, pos_y = _resolve_position(resolved_id, ref, x, y)

    with device_manager.get_device(device_id) as device:
        device.long_click(pos_x, pos_y, duration=duration)

    description = _describe_target(element, ref, (pos_x, pos_y))
    logger.info(f"Long-pressed at ({pos_x}, {pos_y}) for {duration}s: {description}")

    return {
        "success": True,
        "position": {"x": pos_x, "y": pos_y},
        "element": element,
        "ref": ref,
        "duration": duration,
    }


@wrap_tool_errors(logger, "Type failed", pass_through=_INTERACTION_PASSTHROUGH)
def device_type(
    text: str,
    ref: Optional[str] = None,
    device_id: Optional[str] = None,
    element: Optional[str] = None,
    clear_first: bool = False,
    submit: bool = False,
) -> Dict[str, Any]:
    """Type text into an input field.

    If ref is provided, taps on the element first to focus it.
    Then types the specified text.

    Args:
        text: Text to type
        ref: Element ref ID to focus before typing (optional)
        device_id: Device serial (None for default/selected device)
        element: Human-readable element description
        clear_first: Clear existing text before typing
        submit: Press Enter after typing

    Returns:
        Dictionary containing:
        - success: True if typing was successful
        - text: The text that was typed
        - ref: The ref used (if applicable)
        - cleared: Whether text was cleared first
        - submitted: Whether Enter was pressed

    Example:
        >>> # Type into focused field
        >>> device_type(text="hello@example.com")

        >>> # Type into specific field
        >>> device_type(ref="e3", text="password123", element="Password field")

    Raises:
        RefNotFoundError: Ref not found in snapshot
        StaleRefError: Snapshot is too old
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        # Focus element if ref provided
        if ref:
            resolved_id = device_manager.resolve_device_id_or_default(device_id)
            pos_x, pos_y = _resolve_position(resolved_id, ref)
            device.click(pos_x, pos_y)
            time.sleep(0.3)  # Wait for focus

        # Clear existing text if requested
        if clear_first:
            device.clear_text()
            time.sleep(0.1)

        # Type text
        device.send_keys(text)

        # Submit if requested
        if submit:
            device.press("enter")

    description = _describe_target(element, ref)
    logger.info(f"Typed {_redact_text(text)} into {description}")

    return {
        "success": True,
        "text": text,
        "ref": ref,
        "element": element,
        "cleared": clear_first,
        "submitted": submit,
    }


@wrap_tool_errors(logger, "Swipe failed", pass_through=_INTERACTION_PASSTHROUGH)
def device_swipe(
    start_ref: Optional[str] = None,
    end_ref: Optional[str] = None,
    start_x: Optional[int] = None,
    start_y: Optional[int] = None,
    end_x: Optional[int] = None,
    end_y: Optional[int] = None,
    device_id: Optional[str] = None,
    duration: float = 0.5,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Swipe from one point to another.

    Can use refs, coordinates, or direction shortcuts.

    Args:
        start_ref: Starting element ref ID
        end_ref: Ending element ref ID
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        device_id: Device serial (None for default/selected device)
        duration: Swipe duration in seconds
        direction: Shortcut for common swipes: "up", "down", "left", "right"

    Returns:
        Dictionary with success status and swipe info

    Example:
        >>> # Swipe using coordinates
        >>> device_swipe(start_x=500, start_y=1500, end_x=500, end_y=500)

        >>> # Swipe using direction shortcut
        >>> device_swipe(direction="up")

    Raises:
        ValueError: Invalid parameters
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        window = device.window_size()
        width, height = window[0], window[1]

        # Handle direction shortcuts
        if direction:
            center_x = width // 2
            center_y = height // 2
            offset = min(width, height) // 3

            direction_map = {
                "up": (center_x, center_y + offset, center_x, center_y - offset),
                "down": (center_x, center_y - offset, center_x, center_y + offset),
                "left": (center_x + offset, center_y, center_x - offset, center_y),
                "right": (center_x - offset, center_y, center_x + offset, center_y),
            }

            if direction.lower() not in direction_map:
                raise ValueError(
                    f"Invalid direction: {direction}. "
                    "Use 'up', 'down', 'left', or 'right'"
                )

            sx, sy, ex, ey = direction_map[direction.lower()]
        else:
            # Resolve start position
            resolved_id = device_manager.resolve_device_id_or_default(device_id)
            if start_ref:
                sx, sy = _resolve_position(resolved_id, start_ref)
            elif start_x is not None and start_y is not None:
                sx, sy = start_x, start_y
            else:
                raise ValueError("Provide start_ref or start_x/start_y")

            # Resolve end position
            if end_ref:
                ex, ey = _resolve_position(resolved_id, end_ref)
            elif end_x is not None and end_y is not None:
                ex, ey = end_x, end_y
            else:
                raise ValueError("Provide end_ref or end_x/end_y")

        # Execute swipe
        device.swipe(sx, sy, ex, ey, duration=duration)

    logger.info(f"Swiped from ({sx}, {sy}) to ({ex}, {ey})")

    return {
        "success": True,
        "start": {"x": sx, "y": sy},
        "end": {"x": ex, "y": ey},
        "direction": direction,
        "duration": duration,
    }


@wrap_tool_errors(logger, "Clear text failed", pass_through=_INTERACTION_PASSTHROUGH)
def clear_text(
    ref: Optional[str] = None,
    device_id: Optional[str] = None,
    element: Optional[str] = None,
) -> Dict[str, Any]:
    """Clear text from an input field.

    Args:
        ref: Element ref ID to clear (optional, uses focused element if not provided)
        device_id: Device serial (None for default/selected device)
        element: Human-readable element description

    Returns:
        Dictionary with success status

    Raises:
        DeviceConnectionError: Failed to connect to device
    """
    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        # Focus element if ref provided
        if ref:
            resolved_id = device_manager.resolve_device_id_or_default(device_id)
            pos_x, pos_y = _resolve_position(resolved_id, ref)
            device.click(pos_x, pos_y)
            time.sleep(0.3)

        device.clear_text()

    description = _describe_target(element, ref)
    logger.info(f"Cleared text from {description}")

    return {
        "success": True,
        "ref": ref,
        "element": element,
    }
