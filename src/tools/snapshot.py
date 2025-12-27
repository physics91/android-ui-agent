"""Snapshot tools for Android UI Agent - Playwright style.

Provides UI snapshot with ref ID system, screenshot capture, and element finding.
"""
import base64
import logging
from contextlib import closing
from io import BytesIO
from typing import Any, Dict, Optional

from ..core import Snapshot, get_device_manager, get_snapshot_manager
from ._errors import wrap_tool_errors

logger = logging.getLogger(__name__)


def _capture_snapshot(device_id: Optional[str] = None) -> Snapshot:
    """Capture a snapshot and return the Snapshot object."""
    device_manager = get_device_manager()
    snapshot_manager = get_snapshot_manager()

    with device_manager.get_device(device_id) as device:
        current_app = device.app_current()
        package = current_app.get("package", "unknown")
        activity = current_app.get("activity", "unknown")

        window_size = device.window_size()
        screen_size = (window_size[0], window_size[1])

        xml_content = device.dump_hierarchy()

        resolved_id = device_manager.resolve_device_id_or_default(device_id)
        return snapshot_manager.create_snapshot(
            device_id=resolved_id,
            xml_content=xml_content,
            package=package,
            activity=activity,
            screen_size=screen_size,
        )


@wrap_tool_errors(logger, "Failed to capture snapshot")
def device_snapshot(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Capture UI snapshot with Playwright-style ref IDs.

    This is the core tool for UI automation. Each UI element gets a unique
    ref ID (e.g., "e0", "e1") that can be used for subsequent interactions.

    Args:
        device_id: Device serial (None for default/selected device)

    Returns:
        Dictionary containing:
        - snapshot_id: Unique snapshot identifier
        - url: Current app package/activity (like browser URL)
        - screen_size: {width, height}
        - element_count: Total number of elements
        - refs: Dictionary mapping ref IDs to element info
            - Each element has: class, text, content-desc, resource-id,
              bounds, center, clickable, enabled, etc.

    Example:
        >>> snapshot = device_snapshot()
        >>> # Find login button
        >>> for ref, elem in snapshot["refs"].items():
        ...     if elem.get("text") == "Login":
        ...         print(f"Found at ref: {ref}")
        >>> # Use ref for interaction
        >>> device_tap(ref="e5")

    Raises:
        DeviceConnectionError: Failed to connect to device
        RuntimeError: Failed to capture snapshot
    """
    snapshot = _capture_snapshot(device_id)
    logger.info(
        f"Snapshot created: {snapshot.snapshot_id} "
        f"({len(snapshot.refs)} elements)"
    )
    return snapshot.to_dict()


@wrap_tool_errors(logger, "Failed to capture screenshot", pass_through=(ValueError,))
def screenshot(
    device_id: Optional[str] = None,
    quality: int = 80,
    scale: float = 1.0,
) -> Dict[str, Any]:
    """Capture screenshot as base64 PNG.

    Unlike device_snapshot, this returns an actual image that can be displayed
    or analyzed by vision models.

    Args:
        device_id: Device serial (None for default/selected device)
        quality: PNG compression quality hint (1-100, lossless)
        scale: Scale factor (0.1-1.0, lower = smaller file)

    Returns:
        Dictionary containing:
        - image: Base64 encoded PNG image data
        - format: "png"
        - width: Image width in pixels
        - height: Image height in pixels
        - size_bytes: Approximate size of base64 data

    Raises:
        DeviceConnectionError: Failed to connect to device
        RuntimeError: Failed to capture screenshot
    """
    if not (0.1 <= scale <= 1.0):
        raise ValueError("scale must be between 0.1 and 1.0")
    if not (1 <= quality <= 100):
        raise ValueError("quality must be between 1 and 100")

    device_manager = get_device_manager()

    with device_manager.get_device(device_id) as device:
        img = device.screenshot(format="pillow")

        # Apply scaling if requested
        if scale < 1.0:
            new_width = max(1, int(img.width * scale))
            new_height = max(1, int(img.height * scale))
            img = img.resize((new_width, new_height))

        # Convert to base64
        with closing(BytesIO()) as buffer:
            # Map "quality" to PNG compression level (0-9); PNG is lossless.
            compress_level = int(round((100 - quality) / 100 * 9))
            compress_level = max(0, min(9, compress_level))
            img.save(buffer, format="PNG", optimize=True, compress_level=compress_level)
            base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        logger.info(
            f"Screenshot captured: {img.width}x{img.height}, "
            f"{len(base64_data)} bytes (base64)"
        )

        return {
            "image": base64_data,
            "format": "png",
            "width": img.width,
            "height": img.height,
            "size_bytes": len(base64_data),
        }


def find_element(
    device_id: Optional[str] = None,
    text: Optional[str] = None,
    text_contains: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_id_contains: Optional[str] = None,
    class_name: Optional[str] = None,
    content_desc: Optional[str] = None,
    clickable: Optional[bool] = None,
    enabled: Optional[bool] = None,
    refresh_snapshot: bool = False,
) -> Dict[str, Any]:
    """Find elements matching criteria in current snapshot.

    Uses the most recent snapshot to find matching elements. If no snapshot
    exists or refresh_snapshot is True, takes a new snapshot first.

    Args:
        device_id: Device serial (None for default/selected device)
        text: Exact text match
        text_contains: Partial text match
        resource_id: Exact resource ID match
        resource_id_contains: Partial resource ID match
        class_name: Exact class name (e.g., "android.widget.Button")
        content_desc: Exact content description match
        clickable: Filter by clickable state
        enabled: Filter by enabled state
        refresh_snapshot: Force new snapshot before searching

    Returns:
        Dictionary containing:
        - count: Number of matching elements
        - elements: List of matching elements with their refs
        - snapshot_id: ID of the snapshot used

    Raises:
        DeviceConnectionError: Failed to connect to device
        ElementNotFoundError: No elements match criteria (if strict mode)
    """
    device_manager = get_device_manager()
    snapshot_manager = get_snapshot_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    # Refresh snapshot if needed
    if refresh_snapshot or not snapshot_manager.get_current_snapshot(resolved_id):
        device_snapshot(device_id)

    # Get current snapshot
    snapshot = snapshot_manager.get_current_snapshot(resolved_id)
    if not snapshot:
        raise RuntimeError("No snapshot available")

    # Find matching elements
    matches = snapshot.find_elements(
        text=text,
        text_contains=text_contains,
        resource_id=resource_id,
        resource_id_contains=resource_id_contains,
        class_name=class_name,
        content_desc=content_desc,
        clickable=clickable,
        enabled=enabled,
    )

    logger.info(f"Found {len(matches)} elements matching criteria")

    return {
        "count": len(matches),
        "elements": [
            {"ref": elem.ref, **elem.to_dict()} for elem in matches
        ],
        "snapshot_id": snapshot.snapshot_id,
    }
