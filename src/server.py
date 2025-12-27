"""Android UI Agent MCP Server v2.0 - Playwright-style Android Automation.

A comprehensive MCP server for Android UI automation with features matching
Playwright MCP's capabilities.

Key Features:
    - Playwright-style ref system: Elements get unique IDs (e.g., "e0", "e1")
    - Multi-device support: List, select, and switch between devices
    - Complete interaction suite: tap, swipe, type, long-press, etc.
    - Element finding: Search by text, resource-id, class, etc.

Basic Workflow:
    1. Take a snapshot to get element refs
    2. Use refs to interact with elements
    3. Take new snapshot to verify changes

Example:
    >>> # 1. Capture snapshot
    >>> snapshot = device_snapshot()
    >>> # Returns refs like {"e0": {...}, "e1": {...}}

    >>> # 2. AI analyzes and interacts using refs
    >>> device_tap(ref="e5", element="Login button")
    >>> device_type(ref="e3", text="user@example.com")

    >>> # 3. Verify with new snapshot
    >>> snapshot = device_snapshot()

Tools Available:
    Device Management:
        - device_list: List connected devices
        - device_select: Set default device
        - device_info: Get device details
        - device_unlock: Unlock screen

    Snapshot & Elements:
        - device_snapshot: UI snapshot with refs (core tool)
        - screenshot: Capture screen image
        - find_element: Search for elements

    Interactions:
        - device_tap: Tap on element
        - device_double_tap: Double tap
        - device_long_press: Long press
        - device_type: Type text
        - device_swipe: Swipe gesture
        - clear_text: Clear text field
"""
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Import core modules for validation
from .core import get_device_manager, validate_device_id

# Import tool implementations
from .tools.device import (
    device_info as _device_info,
    device_list as _device_list,
    device_select as _device_select,
    device_unlock as _device_unlock,
)
from .tools.interaction import (
    clear_text as _clear_text,
    device_double_tap as _device_double_tap,
    device_long_press as _device_long_press,
    device_swipe as _device_swipe,
    device_tap as _device_tap,
    device_type as _device_type,
)
from .tools.navigation import (
    app_current as _app_current,
    app_start as _app_start,
    app_stop as _app_stop,
    go_back as _go_back,
    go_home as _go_home,
    open_notification as _open_notification,
    open_quick_settings as _open_quick_settings,
    press_key as _press_key,
    set_orientation as _set_orientation,
)
from .tools.snapshot import (
    device_snapshot as _device_snapshot,
    find_element as _find_element,
    screenshot as _screenshot,
)
from .tools.wait import (
    wait as _wait,
    wait_for_activity as _wait_for_activity,
    wait_for_element as _wait_for_element,
    wait_for_element_gone as _wait_for_element_gone,
    wait_for_text as _wait_for_text,
)
from .tools.watcher import (
    watcher_add as _watcher_add,
    watcher_list as _watcher_list,
    watcher_remove as _watcher_remove,
    watcher_start as _watcher_start,
    watcher_stop as _watcher_stop,
    watcher_trigger_once as _watcher_trigger_once,
)
from .tools.recording import (
    add_gesture_event as _add_gesture_event,
    delete_gesture_recording as _delete_gesture_recording,
    export_gesture_recording as _export_gesture_recording,
    import_gesture_recording as _import_gesture_recording,
    list_gesture_recordings as _list_gesture_recordings,
    play_gesture_recording as _play_gesture_recording,
    start_gesture_recording as _start_gesture_recording,
    stop_gesture_recording as _stop_gesture_recording,
)
from .tools.performance import (
    get_performance_metrics as _get_performance_metrics,
    start_performance_monitor as _start_performance_monitor,
    stop_performance_monitor as _stop_performance_monitor,
)

# MCP Server
mcp = FastMCP("android-ui-agent")

# Re-export cache lock for backwards compatibility with tests
_cache_lock = get_device_manager()._cache_lock


# === Tool registrations ===

def _register_tool(func, name: Optional[str] = None):
    return mcp.tool(name=name)(func)


# Backwards compatibility alias
def capture_screenshot(device_id: Optional[str] = None) -> str:
    """Legacy screenshot function (returns base64 string directly).

    Deprecated: Use screenshot() instead.
    """
    if not validate_device_id(device_id):
        raise ValueError(f"Invalid device_id format: {device_id}")
    result = _screenshot(device_id)
    return result["image"]


# Backwards compatibility alias
def dump_ui_hierarchy(device_id: Optional[str] = None, pretty: bool = False) -> str:
    """Legacy UI hierarchy function (returns XML string directly).

    Deprecated: Use device_snapshot() for ref-based workflow.
    """
    if not validate_device_id(device_id):
        raise ValueError(f"Invalid device_id format: {device_id}")

    device_manager = get_device_manager()
    with device_manager.get_device(device_id) as device:
        return device.dump_hierarchy(pretty=pretty)


# === Tool Registrations ===

_TOOL_SECTIONS = (
    {
        # Device Management Tools
        "device_list": _device_list,
        "device_select": _device_select,
        "device_info": _device_info,
        "device_unlock": _device_unlock,
    },
    {
        # Snapshot & Element Tools
        "device_snapshot": _device_snapshot,
        "screenshot": _screenshot,
        "find_element": _find_element,
    },
    {
        # Interaction Tools
        "device_tap": _device_tap,
        "device_double_tap": _device_double_tap,
        "device_long_press": _device_long_press,
        "device_type": _device_type,
        "device_swipe": _device_swipe,
        "clear_text": _clear_text,
    },
    {
        # Navigation Tools
        "app_start": _app_start,
        "app_stop": _app_stop,
        "app_current": _app_current,
        "go_back": _go_back,
        "go_home": _go_home,
        "press_key": _press_key,
        "open_notification": _open_notification,
        "open_quick_settings": _open_quick_settings,
        "set_orientation": _set_orientation,
    },
    {
        # Wait Tools
        "wait_seconds": _wait,
        "wait_for_element": _wait_for_element,
        "wait_for_text": _wait_for_text,
        "wait_for_activity": _wait_for_activity,
        "wait_for_element_gone": _wait_for_element_gone,
    },
    {
        # Watcher Tools
        "watcher_add": _watcher_add,
        "watcher_remove": _watcher_remove,
        "watcher_list": _watcher_list,
        "watcher_start": _watcher_start,
        "watcher_stop": _watcher_stop,
        "watcher_trigger_once": _watcher_trigger_once,
    },
    {
        # Recording Tools
        "start_gesture_recording": _start_gesture_recording,
        "add_gesture_event": _add_gesture_event,
        "stop_gesture_recording": _stop_gesture_recording,
        "play_gesture_recording": _play_gesture_recording,
        "list_gesture_recordings": _list_gesture_recordings,
        "export_gesture_recording": _export_gesture_recording,
        "import_gesture_recording": _import_gesture_recording,
        "delete_gesture_recording": _delete_gesture_recording,
    },
    {
        # Performance Tools
        "get_performance_metrics": _get_performance_metrics,
        "start_performance_monitor": _start_performance_monitor,
        "stop_performance_monitor": _stop_performance_monitor,
    },
)

for _section in _TOOL_SECTIONS:
    for _name, _func in _section.items():
        globals()[_name] = _register_tool(_func, name=_name)


# === Entry Point ===

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    mcp.run()
