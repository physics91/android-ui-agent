"""Playwright-style ref system for Android UI elements.

This module provides a ref ID management system similar to Playwright MCP.
Each UI element gets a unique ref ID (e.g., "e0", "e1") when a snapshot is taken.
These refs can then be used to interact with elements.

Usage:
    # 1. Take a snapshot
    snapshot = device_snapshot()
    # {"refs": {"e0": {...}, "e1": {...}}}

    # 2. Use ref to interact
    device_tap(ref="e0")
"""

import hashlib
from itertools import count
import logging
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

# Try to import defusedxml for security; fallback to standard library with warning
try:
    import defusedxml.ElementTree as DefusedET
    _USE_DEFUSEDXML = True
except ImportError:
    DefusedET = ET  # type: ignore
    _USE_DEFUSEDXML = False

from .exceptions import RefNotFoundError, StaleRefError

logger = logging.getLogger(__name__)

if not _USE_DEFUSEDXML:
    logger.warning(
        "defusedxml not installed. XML parsing is less secure. "
        "Install with: pip install defusedxml"
    )

_BOUNDS_RE = re.compile(r"\d+")


@dataclass
class ElementInfo:
    """Information about a single UI element."""

    ref: str  # e.g., "e0", "e1"
    class_name: str  # e.g., "android.widget.Button"
    bounds: Tuple[int, int, int, int]  # (left, top, right, bottom)
    resource_id: Optional[str] = None
    text: Optional[str] = None
    content_desc: Optional[str] = None
    package: Optional[str] = None
    clickable: bool = False
    focusable: bool = False
    enabled: bool = True
    checked: Optional[bool] = None
    selected: bool = False
    scrollable: bool = False
    long_clickable: bool = False
    index: int = 0

    @property
    def center(self) -> Tuple[int, int]:
        """Get center coordinates of the element."""
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def width(self) -> int:
        """Get element width."""
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self) -> int:
        """Get element height."""
        return self.bounds[3] - self.bounds[1]

    def to_dict(self) -> dict:
        """Convert to dictionary for MCP response."""
        return {
            "class": self.class_name,
            "text": self.text,
            "content-desc": self.content_desc,
            "resource-id": self.resource_id,
            "bounds": list(self.bounds),
            "center": list(self.center),
            "clickable": self.clickable,
            "focusable": self.focusable,
            "enabled": self.enabled,
            "scrollable": self.scrollable,
            "selected": self.selected,
        }

    def matches(
        self,
        text: Optional[str] = None,
        text_contains: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_id_contains: Optional[str] = None,
        class_name: Optional[str] = None,
        content_desc: Optional[str] = None,
        clickable: Optional[bool] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """Check if element matches the given criteria."""
        if text is not None and self.text != text:
            return False
        if text_contains is not None and (
            self.text is None or text_contains not in self.text
        ):
            return False
        if resource_id is not None and self.resource_id != resource_id:
            return False
        if resource_id_contains is not None and (
            self.resource_id is None or resource_id_contains not in self.resource_id
        ):
            return False
        if class_name is not None and self.class_name != class_name:
            return False
        if content_desc is not None and self.content_desc != content_desc:
            return False
        if clickable is not None and self.clickable != clickable:
            return False
        if enabled is not None and self.enabled != enabled:
            return False
        return True


def _parse_bounds(bounds_str: str) -> Tuple[int, int, int, int]:
    """Parse bounds string '[100,200][300,400]' -> (100, 200, 300, 400)."""
    match = _BOUNDS_RE.findall(bounds_str)
    if len(match) >= 4:
        return tuple(map(int, match[:4]))
    logger.debug(f"Invalid bounds string: {bounds_str}")
    return (0, 0, 0, 0)


@dataclass
class Snapshot:
    """A snapshot of device UI state with ref mappings."""

    snapshot_id: str
    device_id: str
    package: str
    activity: str
    timestamp: float
    screen_size: Tuple[int, int]  # (width, height)
    refs: Dict[str, ElementInfo] = field(default_factory=dict)
    xml_hash: str = ""

    def is_stale(self, max_age_seconds: float = 30.0) -> bool:
        """Check if snapshot is too old."""
        return time.time() - self.timestamp > max_age_seconds

    @property
    def age_seconds(self) -> float:
        """Get snapshot age in seconds."""
        return time.time() - self.timestamp

    def get_element(self, ref: str) -> Optional[ElementInfo]:
        """Get element by ref ID."""
        return self.refs.get(ref)

    def find_elements(self, **criteria) -> List[ElementInfo]:
        """Find elements matching criteria."""
        return [elem for elem in self.refs.values() if elem.matches(**criteria)]

    def to_dict(self) -> dict:
        """Convert to dictionary for MCP response."""
        return {
            "snapshot_id": self.snapshot_id,
            "url": f"{self.package}/{self.activity}",
            "screen_size": {"width": self.screen_size[0], "height": self.screen_size[1]},
            "element_count": len(self.refs),
            "timestamp": self.timestamp,
            "refs": {ref: elem.to_dict() for ref, elem in self.refs.items()},
        }


class SnapshotManager:
    """Manages snapshots and ref mappings for multiple devices.

    Thread-safe implementation for concurrent access.
    """

    def __init__(self, max_snapshots_per_device: int = 5, default_stale_seconds: float = 30.0):
        self._snapshots: Dict[str, Dict[str, Snapshot]] = {}  # device_id -> {id: Snapshot}
        self._snapshot_order: Dict[str, Deque[str]] = {}  # device_id -> [snapshot_id]
        self._current: Dict[str, str] = {}  # device_id -> snapshot_id
        self._lock = threading.Lock()
        self._max_snapshots = max_snapshots_per_device
        self._default_stale_seconds = default_stale_seconds

    def create_snapshot(
        self,
        device_id: str,
        xml_content: str,
        package: str,
        activity: str,
        screen_size: Tuple[int, int],
    ) -> Snapshot:
        """Create a new snapshot from UI hierarchy XML.

        Args:
            device_id: Device identifier
            xml_content: UI hierarchy XML string
            package: Current app package name
            activity: Current activity name
            screen_size: (width, height) tuple

        Returns:
            New Snapshot with ref mappings
        """
        with self._lock:
            # Parse XML and generate refs
            refs = self._parse_hierarchy(xml_content)

            # Create snapshot with unique ID
            snapshot_id = f"{device_id}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                device_id=device_id,
                package=package,
                activity=activity,
                timestamp=time.time(),
                screen_size=screen_size,
                refs=refs,
                xml_hash=hashlib.md5(xml_content.encode()).hexdigest(),
            )

            # Store in cache
            if device_id not in self._snapshots:
                self._snapshots[device_id] = {}
                self._snapshot_order[device_id] = deque()
            self._snapshots[device_id][snapshot_id] = snapshot
            self._snapshot_order[device_id].append(snapshot_id)

            # Cleanup old snapshots (ensure max is at least 1)
            max_allowed = max(1, self._max_snapshots)
            while len(self._snapshot_order[device_id]) > max_allowed:
                old_id = self._snapshot_order[device_id].popleft()
                self._snapshots[device_id].pop(old_id, None)

            # Set as current
            self._current[device_id] = snapshot_id

            return snapshot

    def _parse_hierarchy(self, xml_content: str) -> Dict[str, ElementInfo]:
        """Parse UI hierarchy XML and generate ref mappings."""
        refs: Dict[str, ElementInfo] = {}
        counter = count()

        def traverse(node: ET.Element):
            """Recursively traverse and assign refs."""
            attrib = node.attrib
            bounds = _parse_bounds(attrib.get("bounds", "[0,0][0,0]"))

            # Only create ref for elements with valid bounds
            if bounds != (0, 0, 0, 0):
                ref = f"e{next(counter)}"

                element = ElementInfo(
                    ref=ref,
                    class_name=attrib.get("class", "node"),
                    bounds=bounds,
                    resource_id=attrib.get("resource-id") or None,
                    text=attrib.get("text") or None,
                    content_desc=attrib.get("content-desc") or None,
                    package=attrib.get("package") or None,
                    clickable=attrib.get("clickable") == "true",
                    focusable=attrib.get("focusable") == "true",
                    enabled=attrib.get("enabled", "true") == "true",
                    checked=(
                        attrib.get("checked") == "true"
                        if "checked" in attrib
                        else None
                    ),
                    selected=attrib.get("selected") == "true",
                    scrollable=attrib.get("scrollable") == "true",
                    long_clickable=attrib.get("long-clickable") == "true",
                    index=int(attrib.get("index", 0)),
                )
                refs[ref] = element

            # Process children
            for child in node:
                traverse(child)

        try:
            # Use defusedxml to prevent XXE attacks
            root = DefusedET.fromstring(xml_content)
            # Handle both <hierarchy> and direct <node> roots
            if root.tag == "hierarchy":
                for child in root:
                    traverse(child)
            else:
                traverse(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        except Exception as e:
            # defusedxml may raise different exceptions for malicious XML
            logger.warning(f"XML parsing rejected (possible security issue): {e}")
            raise ValueError(f"Invalid or potentially malicious XML: {e}")

        return refs

    def get_current_snapshot(self, device_id: str) -> Optional[Snapshot]:
        """Get the current active snapshot for a device."""
        with self._lock:
            snapshot_id = self._current.get(device_id)
            if not snapshot_id:
                return None
            return self._snapshots.get(device_id, {}).get(snapshot_id)

    def resolve_ref(
        self,
        device_id: str,
        ref: str,
        validate_staleness: bool = True,
        max_stale_seconds: Optional[float] = None,
    ) -> ElementInfo:
        """Resolve a ref to ElementInfo.

        Args:
            device_id: Device identifier
            ref: Ref ID (e.g., "e5")
            validate_staleness: Whether to check snapshot age
            max_stale_seconds: Max allowed snapshot age

        Returns:
            ElementInfo for the ref

        Raises:
            RefNotFoundError: If no snapshot or ref not found
            StaleRefError: If snapshot is too old
        """
        snapshot = self.get_current_snapshot(device_id)
        if not snapshot:
            raise RefNotFoundError(ref, [])

        if validate_staleness:
            max_age = max_stale_seconds or self._default_stale_seconds
            if snapshot.is_stale(max_age):
                raise StaleRefError(ref, snapshot.age_seconds)

        element = snapshot.get_element(ref)
        if not element:
            available = list(snapshot.refs.keys())
            raise RefNotFoundError(ref, available)

        return element

    def get_position(self, device_id: str, ref: str) -> Tuple[int, int]:
        """Get center position for a ref (for tap/click operations)."""
        element = self.resolve_ref(device_id, ref)
        return element.center

    def find_elements(self, device_id: str, **criteria) -> List[ElementInfo]:
        """Find elements matching criteria in current snapshot."""
        snapshot = self.get_current_snapshot(device_id)
        if not snapshot:
            return []
        return snapshot.find_elements(**criteria)

    def invalidate(self, device_id: str):
        """Invalidate all snapshots for a device."""
        with self._lock:
            self._snapshots.pop(device_id, None)
            self._snapshot_order.pop(device_id, None)
            self._current.pop(device_id, None)

    def clear_all(self):
        """Clear all snapshots for all devices."""
        with self._lock:
            self._snapshots.clear()
            self._snapshot_order.clear()
            self._current.clear()


# Global singleton
_snapshot_manager: Optional[SnapshotManager] = None
_manager_lock = threading.Lock()


def get_snapshot_manager() -> SnapshotManager:
    """Get the global SnapshotManager instance."""
    global _snapshot_manager
    with _manager_lock:
        if _snapshot_manager is None:
            _snapshot_manager = SnapshotManager()
        return _snapshot_manager
