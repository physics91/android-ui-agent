"""MCP Tools for Android UI Agent.

This package contains all MCP tool implementations organized by functionality.
"""
from .device import device_list, device_select, device_info, device_unlock
from .snapshot import device_snapshot, screenshot, find_element
from .interaction import (
    device_tap,
    device_double_tap,
    device_long_press,
    device_type,
    device_swipe,
    clear_text,
)
from .navigation import (
    app_start,
    app_stop,
    app_current,
    go_back,
    go_home,
    press_key,
    open_notification,
    open_quick_settings,
    set_orientation,
)
from .wait import (
    wait,
    wait_for_element,
    wait_for_text,
    wait_for_activity,
    wait_for_element_gone,
)
from .watcher import (
    watcher_add,
    watcher_remove,
    watcher_list,
    watcher_start,
    watcher_stop,
    watcher_trigger_once,
    get_watcher_manager,
)
from .recording import (
    start_gesture_recording,
    add_gesture_event,
    stop_gesture_recording,
    play_gesture_recording,
    list_gesture_recordings,
    export_gesture_recording,
    import_gesture_recording,
    delete_gesture_recording,
    get_recording_manager,
)
from .performance import (
    get_performance_metrics,
    start_performance_monitor,
    stop_performance_monitor,
    get_performance_monitor,
)

__all__ = [
    # Device tools
    "device_list",
    "device_select",
    "device_info",
    "device_unlock",
    # Snapshot tools
    "device_snapshot",
    "screenshot",
    "find_element",
    # Interaction tools
    "device_tap",
    "device_double_tap",
    "device_long_press",
    "device_type",
    "device_swipe",
    "clear_text",
    # Navigation tools
    "app_start",
    "app_stop",
    "app_current",
    "go_back",
    "go_home",
    "press_key",
    "open_notification",
    "open_quick_settings",
    "set_orientation",
    # Wait tools
    "wait",
    "wait_for_element",
    "wait_for_text",
    "wait_for_activity",
    "wait_for_element_gone",
    # Watcher tools
    "watcher_add",
    "watcher_remove",
    "watcher_list",
    "watcher_start",
    "watcher_stop",
    "watcher_trigger_once",
    "get_watcher_manager",
    # Recording tools
    "start_gesture_recording",
    "add_gesture_event",
    "stop_gesture_recording",
    "play_gesture_recording",
    "list_gesture_recordings",
    "export_gesture_recording",
    "import_gesture_recording",
    "delete_gesture_recording",
    "get_recording_manager",
    # Performance tools
    "get_performance_metrics",
    "start_performance_monitor",
    "stop_performance_monitor",
    "get_performance_monitor",
]
