"""Watcher tools for Android UI Agent.

Provides automatic popup/dialog handling with background monitoring.
Similar to uiautomator2's watcher functionality but with MCP integration.
"""
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core import DeviceConnectionError, get_device_manager

logger = logging.getLogger(__name__)


@dataclass
class WatcherCondition:
    """A condition that triggers a watcher."""

    type: str  # "text", "text_contains", "resource_id", "resource_id_contains"
    value: str


@dataclass
class WatcherRule:
    """A watcher rule that defines trigger conditions and action."""

    name: str
    conditions: List[WatcherCondition]
    action: str  # "click", "back", "home", "press:<key>"
    action_target: Optional[str] = None  # For click: which condition element to click
    priority: int = 0
    enabled: bool = True
    trigger_count: int = 0
    last_triggered: Optional[float] = None


def _build_selector(condition: WatcherCondition) -> Optional[Dict[str, str]]:
    """Build a uiautomator2 selector from a watcher condition."""
    if condition.type == "text":
        return {"text": condition.value}
    if condition.type == "text_contains":
        return {"textContains": condition.value}
    if condition.type == "resource_id":
        return {"resourceId": condition.value}
    if condition.type == "resource_id_contains":
        # Security: Escape regex special characters to prevent injection.
        escaped_value = re.escape(condition.value)
        return {"resourceIdMatches": f".*{escaped_value}.*"}
    return None


def _perform_action(action: str, device, click_element) -> None:
    """Execute a watcher action on the device."""
    if action == "click":
        if click_element is not None:
            click_element.click()
        return
    if action == "back":
        device.press("back")
        return
    if action == "home":
        device.press("home")
        return
    if action.startswith("press:"):
        key = action.split(":", 1)[1]
        device.press(key)


class WatcherManager:
    """Manages watchers for automatic popup handling.

    Watchers run in a background thread and periodically check for
    matching elements. When found, they execute the configured action.
    """

    def __init__(self):
        self._watchers: Dict[str, Dict[str, WatcherRule]] = {}  # device_id -> {name: rule}
        self._running: Dict[str, bool] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self._poll_interval = 1.0  # seconds

    def add_watcher(
        self,
        device_id: str,
        name: str,
        conditions: List[Dict[str, str]],
        action: str,
        action_target: Optional[str] = None,
        priority: int = 0,
    ) -> WatcherRule:
        """Add a new watcher rule.

        Args:
            device_id: Device identifier
            name: Unique watcher name
            conditions: List of condition dicts with 'type' and 'value'
            action: Action to perform: "click", "back", "home", "press:<key>"
            action_target: For click action, which condition index to click (default: first)
            priority: Higher priority runs first

        Returns:
            Created WatcherRule
        """
        parsed_conditions = [
            WatcherCondition(type=c["type"], value=c["value"]) for c in conditions
        ]

        rule = WatcherRule(
            name=name,
            conditions=parsed_conditions,
            action=action,
            action_target=action_target,
            priority=priority,
        )

        with self._lock:
            if device_id not in self._watchers:
                self._watchers[device_id] = {}
            self._watchers[device_id][name] = rule

        logger.info(f"Added watcher '{name}' for device '{device_id}'")
        return rule

    def remove_watcher(self, device_id: str, name: str) -> bool:
        """Remove a watcher by name.

        Returns:
            True if watcher was removed
        """
        with self._lock:
            if device_id in self._watchers and name in self._watchers[device_id]:
                del self._watchers[device_id][name]
                logger.info(f"Removed watcher '{name}' from device '{device_id}'")
                return True
        return False

    def list_watchers(self, device_id: str) -> List[Dict[str, Any]]:
        """List all watchers for a device."""
        with self._lock:
            watchers = self._watchers.get(device_id, {})
            return [
                {
                    "name": rule.name,
                    "conditions": [
                        {"type": c.type, "value": c.value} for c in rule.conditions
                    ],
                    "action": rule.action,
                    "action_target": rule.action_target,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "trigger_count": rule.trigger_count,
                    "last_triggered": rule.last_triggered,
                }
                for rule in watchers.values()
            ]

    def _check_and_trigger(self, device_id: str) -> Optional[str]:
        """Check all watchers and trigger if conditions match.

        Returns:
            Name of triggered watcher, or None
        """
        device_manager = get_device_manager()

        with self._lock:
            watchers = self._watchers.get(device_id, {})
            if not watchers:
                return None

            # Sort by priority (higher first)
            sorted_watchers = sorted(
                watchers.values(), key=lambda w: w.priority, reverse=True
            )

        try:
            with device_manager.get_device(device_id) as device:
                for rule in sorted_watchers:
                    if not rule.enabled:
                        continue

                    # Check all conditions
                    all_match = True
                    click_element = None
                    action_target = (
                        str(rule.action_target)
                        if rule.action_target is not None
                        else None
                    )

                    for i, condition in enumerate(rule.conditions):
                        # Find element matching condition
                        selector = _build_selector(condition)
                        if not selector:
                            continue

                        element = device(**selector)
                        if not element.exists:
                            all_match = False
                            break

                        # Remember first matching element for click
                        # Fix: Ensure proper type comparison for action_target
                        if i == 0 or (action_target is not None and str(i) == action_target):
                            click_element = element

                    if all_match and click_element:
                        _perform_action(rule.action, device, click_element)

                        # Update stats
                        with self._lock:
                            rule.trigger_count += 1
                            rule.last_triggered = time.time()

                        logger.info(f"Watcher '{rule.name}' triggered on device '{device_id}'")
                        return rule.name

        except DeviceConnectionError:
            logger.warning(f"Device disconnected during watcher check: {device_id}")
        except Exception as e:
            logger.error(f"Watcher check failed: {e}")

        return None

    def _watcher_loop(self, device_id: str, poll_interval: float):
        """Background loop that checks watchers."""
        logger.info(f"Watcher loop started for device '{device_id}'")
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._running.get(device_id, False):
            try:
                self._check_and_trigger(device_id)
                consecutive_errors = 0  # Reset on success
            except DeviceConnectionError:
                logger.warning(f"Device disconnected, stopping watcher: {device_id}")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Watcher error ({consecutive_errors}/{max_consecutive_errors}): {e}"
                )
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive errors, stopping watcher: {device_id}"
                    )
                    break

            time.sleep(poll_interval)

        # Cleanup on exit
        with self._lock:
            self._running[device_id] = False
        logger.info(f"Watcher loop stopped for device '{device_id}'")

    def start(self, device_id: str, poll_interval: float = 1.0) -> bool:
        """Start watcher monitoring for a device.

        Args:
            device_id: Device identifier
            poll_interval: Seconds between checks

        Returns:
            True if started
        """
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than 0")
        with self._lock:
            if self._running.get(device_id, False):
                return False  # Already running

            self._running[device_id] = True

            thread = threading.Thread(
                target=self._watcher_loop,
                args=(device_id, poll_interval),
                daemon=True,
                name=f"watcher-{device_id}",
            )
            self._threads[device_id] = thread
            thread.start()

        logger.info(f"Watcher monitoring started for device '{device_id}'")
        return True

    def stop(self, device_id: str) -> Dict[str, Any]:
        """Stop watcher monitoring for a device.

        Returns:
            Summary of watcher activity
        """
        with self._lock:
            self._running[device_id] = False
            thread = self._threads.pop(device_id, None)

        # Wait for thread to finish
        if thread and thread.is_alive():
            thread.join(timeout=2.0)

        # Generate summary
        with self._lock:
            watchers = self._watchers.get(device_id, {})
            summary = {
                "total_watchers": len(watchers),
                "triggers": [
                    {
                        "name": rule.name,
                        "trigger_count": rule.trigger_count,
                        "last_triggered": rule.last_triggered,
                    }
                    for rule in watchers.values()
                    if rule.trigger_count > 0
                ],
            }

        logger.info(f"Watcher monitoring stopped for device '{device_id}'")
        return summary

    def is_running(self, device_id: str) -> bool:
        """Check if watcher is running for device."""
        return self._running.get(device_id, False)

    def reset_stats(self, device_id: str):
        """Reset trigger counts for all watchers."""
        with self._lock:
            watchers = self._watchers.get(device_id, {})
            for rule in watchers.values():
                rule.trigger_count = 0
                rule.last_triggered = None


# Global singleton
_watcher_manager: Optional[WatcherManager] = None
_manager_lock = threading.Lock()


def get_watcher_manager() -> WatcherManager:
    """Get the global WatcherManager instance."""
    global _watcher_manager
    with _manager_lock:
        if _watcher_manager is None:
            _watcher_manager = WatcherManager()
        return _watcher_manager


# === MCP Tool Functions ===


def watcher_add(
    name: str,
    conditions: List[Dict[str, str]],
    action: str = "click",
    device_id: Optional[str] = None,
    action_target: Optional[str] = None,
    priority: int = 0,
) -> Dict[str, Any]:
    """Add a watcher to automatically handle popups/dialogs.

    Watchers monitor the screen and perform actions when matching
    elements are found.

    Args:
        name: Unique watcher name
        conditions: List of conditions, each with:
            - type: "text", "text_contains", "resource_id", "resource_id_contains"
            - value: Value to match
        action: Action to perform when triggered:
            - "click": Click the matched element
            - "back": Press back button
            - "home": Press home button
            - "press:<key>": Press specified key
        device_id: Device serial (None for default)
        action_target: For click, which condition index to click
        priority: Higher priority watchers run first

    Returns:
        Dictionary with watcher info

    Example:
        >>> # Auto-accept permission dialogs
        >>> watcher_add(
        ...     name="permission",
        ...     conditions=[{"type": "text", "value": "ALLOW"}],
        ...     action="click"
        ... )
        >>> watcher_start()

        >>> # Auto-close ads
        >>> watcher_add(
        ...     name="close_ad",
        ...     conditions=[{"type": "resource_id_contains", "value": "close_btn"}],
        ...     action="click"
        ... )
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    rule = manager.add_watcher(
        device_id=resolved_id,
        name=name,
        conditions=conditions,
        action=action,
        action_target=action_target,
        priority=priority,
    )

    return {
        "success": True,
        "name": rule.name,
        "conditions": [{"type": c.type, "value": c.value} for c in rule.conditions],
        "action": rule.action,
        "priority": rule.priority,
    }


def watcher_remove(
    name: str,
    device_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Remove a watcher.

    Args:
        name: Watcher name to remove
        device_id: Device serial (None for default)

    Returns:
        Dictionary with success status
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    removed = manager.remove_watcher(resolved_id, name)

    return {
        "success": removed,
        "name": name,
    }


def watcher_list(device_id: Optional[str] = None) -> Dict[str, Any]:
    """List all registered watchers.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with watcher list
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    watchers = manager.list_watchers(resolved_id)

    return {
        "count": len(watchers),
        "running": manager.is_running(resolved_id),
        "watchers": watchers,
    }


def watcher_start(
    device_id: Optional[str] = None,
    poll_interval: float = 1.0,
) -> Dict[str, Any]:
    """Start background watcher monitoring.

    Args:
        device_id: Device serial (None for default)
        poll_interval: Seconds between checks

    Returns:
        Dictionary with start status
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    started = manager.start(resolved_id, poll_interval)

    return {
        "success": True,
        "started": started,
        "already_running": not started,
        "poll_interval": poll_interval,
    }


def watcher_stop(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Stop background watcher monitoring.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with stop status and activity summary
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    summary = manager.stop(resolved_id)

    return {
        "success": True,
        "summary": summary,
    }


def watcher_trigger_once(device_id: Optional[str] = None) -> Dict[str, Any]:
    """Manually trigger a single watcher check.

    Useful for testing watchers without starting background monitoring.

    Args:
        device_id: Device serial (None for default)

    Returns:
        Dictionary with triggered watcher name (if any)
    """
    device_manager = get_device_manager()
    resolved_id = device_manager.resolve_device_id_or_default(device_id)

    manager = get_watcher_manager()
    triggered = manager._check_and_trigger(resolved_id)

    return {
        "triggered": triggered is not None,
        "watcher_name": triggered,
    }
