import anyio
import json
import os
import sys
from datetime import timedelta

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PKG = "com.example.androidtestapp"


def _unwrap(result):
    if result.isError:
        raise RuntimeError(f"Tool error: {result}")
    if result.structuredContent and "result" in result.structuredContent:
        return result.structuredContent["result"]
    if result.content:
        return json.loads(result.content[0].text)
    return {}


async def call(session, name, args=None, timeout=20):
    result = await session.call_tool(
        name,
        arguments=args or {},
        read_timeout_seconds=timedelta(seconds=timeout),
    )
    return _unwrap(result)


async def wait_for_text(session, text, partial=False, timeout=10):
    return await call(
        session,
        "wait_for_text",
        {
            "text": text,
            "partial": partial,
            "timeout": timeout,
            "poll_interval": 0.5,
        },
        timeout=timeout + 15,
    )


async def try_wait_for_text(session, text, partial=False, timeout=5):
    result = await wait_for_text(session, text, partial=partial, timeout=timeout)
    return result.get("found", False)


async def find_one(session, **criteria):
    result = await call(session, "find_element", {**criteria, "refresh_snapshot": True})
    if result["count"] == 0:
        raise RuntimeError(f"Element not found: {criteria}")
    return result["elements"][0]


async def ensure_on_main(session, attempts=3, relaunch=True):
    for _ in range(attempts):
        result = await wait_for_text(session, "Test Cases", timeout=5)
        if result.get("found"):
            return
        await call(session, "go_back")
    if relaunch:
        await call(session, "app_start", {"package": PKG, "stop_first": False})
        result = await wait_for_text(session, "Test Cases", timeout=10)
        if result.get("found"):
            return
    raise RuntimeError("Failed to return to Test Cases screen")


async def scroll_to_top(session, attempts=4):
    for _ in range(attempts):
        await call(session, "device_swipe", {"direction": "down", "duration": 0.5})


async def swipe_left_on_element(session, element, padding=10, duration=0.3):
    bounds = element["bounds"]
    start_x = bounds[2] - padding
    end_x = bounds[0] + padding
    y = (bounds[1] + bounds[3]) // 2
    await call(
        session,
        "device_swipe",
        {
            "start_x": start_x,
            "start_y": y,
            "end_x": end_x,
            "end_y": y,
            "duration": duration,
        },
    )


async def open_case(session, title):
    await ensure_on_main(session)
    await scroll_to_top(session)
    for _ in range(12):
        result = await call(
            session,
            "find_element",
            {"text": title, "refresh_snapshot": True},
            timeout=20,
        )
        if result.get("count", 0) > 0:
            elem = result["elements"][0]
            await call(session, "device_tap", {"ref": elem["ref"], "element": title})
            return
        await call(session, "device_swipe", {"direction": "up", "duration": 0.5})
    raise RuntimeError(f"Case not found after scrolling: {title}")


async def scroll_until_text(session, text, attempts=5):
    for _ in range(attempts):
        result = await call(
            session,
            "find_element",
            {"text": text, "refresh_snapshot": True},
            timeout=20,
        )
        if result.get("count", 0) > 0:
            return result["elements"][0]
        await call(session, "device_swipe", {"direction": "up", "duration": 0.5})
    raise RuntimeError(f"Failed to find text after scrolling: {text}")


async def run_tests():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "src.server"],
        cwd=os.getcwd(),
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            devices = await call(session, "device_list")
            if devices.get("count", 0) == 0:
                raise RuntimeError("No devices available for testing")

            await call(session, "app_start", {"package": PKG, "stop_first": True})
            await wait_for_text(session, "Test Cases", timeout=15)

            # Controls
            await open_case(session, "Controls")
            await wait_for_text(session, "Submit", timeout=10)
            email = await find_one(session, resource_id=f"{PKG}:id/input_email")
            password = await find_one(session, resource_id=f"{PKG}:id/input_password")
            submit = await find_one(session, text="Submit")
            await call(session, "device_type", {"text": "user@example.com", "ref": email["ref"], "clear_first": True})
            await call(session, "device_type", {"text": "pass1234", "ref": password["ref"], "clear_first": True})
            await call(session, "device_tap", {"ref": submit["ref"], "element": "Submit"})
            await wait_for_text(session, "SUBMITTED", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Lists
            await open_case(session, "Lists")
            await wait_for_text(session, "Selected:", partial=True, timeout=10)
            item20 = await scroll_until_text(session, "Item 20")
            await call(session, "device_tap", {"ref": item20["ref"], "element": "Item 20"})
            await wait_for_text(session, "Selected: Item 20", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Dialogs
            await open_case(session, "Dialogs")
            await wait_for_text(session, "Show Alert", timeout=10)
            alert = await find_one(session, text="Show Alert")
            await call(session, "device_tap", {"ref": alert["ref"], "element": "Show Alert"})
            ok = await wait_for_text(session, "OK", timeout=10)
            if ok.get("found"):
                await call(session, "device_tap", {"ref": ok["ref"], "element": "OK"})
            await wait_for_text(session, "ALERT_OK", partial=True, timeout=10)

            sheet = await find_one(session, text="Show Bottom Sheet")
            await call(session, "device_tap", {"ref": sheet["ref"], "element": "Show Bottom Sheet"})
            sheet_ok = await wait_for_text(session, "Sheet OK", timeout=10)
            if sheet_ok.get("found"):
                await call(session, "device_tap", {"ref": sheet_ok["ref"], "element": "Sheet OK"})
            await wait_for_text(session, "SHEET_OK", partial=True, timeout=10)

            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Gestures
            await open_case(session, "Gestures")
            await wait_for_text(session, "Gesture:", partial=True, timeout=10)
            area = await find_one(session, resource_id=f"{PKG}:id/gesture_area")
            await call(session, "device_double_tap", {"ref": area["ref"], "element": "Gesture Area"})
            await wait_for_text(session, "DOUBLE_TAP", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Permissions
            await open_case(session, "Permissions")
            await wait_for_text(session, "Request Notification Permission", partial=True, timeout=10)
            perm_btn = await find_one(session, text_contains="Request Notification")
            await call(session, "device_tap", {"ref": perm_btn["ref"], "element": "Request Permission"})
            allow = await wait_for_text(session, "Allow", partial=True, timeout=3)
            if allow.get("found"):
                await call(session, "device_tap", {"ref": allow["ref"], "element": "Allow"})
            await try_wait_for_text(session, "Status:", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # WebView
            await open_case(session, "WebView")
            await wait_for_text(session, "Run JS", timeout=10)
            run_js = await find_one(session, text="Run JS")
            await call(session, "device_tap", {"ref": run_js["ref"], "element": "Run JS"})
            await wait_for_text(session, "clicked", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Scrolling
            await open_case(session, "Scrolling")
            await scroll_until_text(session, "Scroll Item 60")

            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Tabs
            await open_case(session, "Tabs")
            await wait_for_text(session, "Tab A Content", timeout=10)
            tab_b = await find_one(session, content_desc="Tab B")
            await call(session, "device_tap", {"ref": tab_b["ref"], "element": "Tab B"})
            await wait_for_text(session, "Tab B Content", timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Notifications
            await open_case(session, "Notifications")
            await wait_for_text(session, "Send Notification", timeout=10)
            send_btn = await find_one(session, text="Send Notification")
            await call(session, "device_tap", {"ref": send_btn["ref"], "element": "Send Notification"})
            await wait_for_text(session, "Status: SENT", partial=True, timeout=10)
            await call(session, "open_notification")
            await wait_for_text(session, "Test Notification", partial=True, timeout=5)
            await call(session, "go_back")
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # File Picker
            await open_case(session, "File Picker")
            await wait_for_text(session, "Open Document", timeout=10)
            open_doc = await find_one(session, text="Open Document")
            await call(session, "device_tap", {"ref": open_doc["ref"], "element": "Open Document"})
            await call(session, "wait_seconds", {"seconds": 2})
            await call(session, "go_back")
            await wait_for_text(session, "Result: Cancelled", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Snackbars & Toasts
            await open_case(session, "Snackbars & Toasts")
            await wait_for_text(session, "Show Snackbar", timeout=10)
            show_snackbar = await find_one(session, text="Show Snackbar")
            await call(session, "device_tap", {"ref": show_snackbar["ref"], "element": "Show Snackbar"})
            await wait_for_text(session, "SNACKBAR_SHOWN", partial=True, timeout=10)
            action_result = await call(
                session,
                "find_element",
                {"text": "Action", "refresh_snapshot": True},
                timeout=20,
            )
            if action_result.get("count", 0) > 0:
                snackbar_action = action_result["elements"][0]
                await call(session, "device_tap", {"ref": snackbar_action["ref"], "element": "Action"})
                await wait_for_text(session, "SNACKBAR_ACTION", partial=True, timeout=10)
            show_toast = await find_one(session, text="Show Toast")
            await call(session, "device_tap", {"ref": show_toast["ref"], "element": "Show Toast"})
            await wait_for_text(session, "TOAST_SHOWN", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Bottom Navigation
            await open_case(session, "Bottom Navigation")
            await wait_for_text(session, "Home Screen", partial=True, timeout=10)
            dashboard = await find_one(session, text="Dashboard")
            await call(session, "device_tap", {"ref": dashboard["ref"], "element": "Dashboard"})
            await wait_for_text(session, "Dashboard Screen", partial=True, timeout=10)
            settings = await find_one(session, text="Settings")
            await call(session, "device_tap", {"ref": settings["ref"], "element": "Settings"})
            await wait_for_text(session, "Settings Screen", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Sliders
            await open_case(session, "Sliders")
            await wait_for_text(session, "Progress:", partial=True, timeout=10)
            increase = await find_one(session, text="Increase")
            await call(session, "device_tap", {"ref": increase["ref"], "element": "Increase"})
            await call(session, "device_tap", {"ref": increase["ref"], "element": "Increase"})
            await wait_for_text(session, "Progress: 20", partial=True, timeout=10)
            decrease = await find_one(session, text="Decrease")
            await call(session, "device_tap", {"ref": decrease["ref"], "element": "Decrease"})
            await wait_for_text(session, "Progress: 10", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Swipe Refresh
            await open_case(session, "Swipe Refresh")
            await wait_for_text(session, "Trigger Refresh", timeout=10)
            trigger = await find_one(session, text="Trigger Refresh")
            await call(session, "device_tap", {"ref": trigger["ref"], "element": "Trigger Refresh"})
            await wait_for_text(session, "Status: Refreshed", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Counter
            await open_case(session, "Counter")
            await wait_for_text(session, "Count: 0", partial=True, timeout=10)
            plus = await find_one(session, text="Plus")
            await call(session, "device_tap", {"ref": plus["ref"], "element": "Plus"})
            await call(session, "device_tap", {"ref": plus["ref"], "element": "Plus"})
            await wait_for_text(session, "Count: 2", partial=True, timeout=10)
            minus = await find_one(session, text="Minus")
            await call(session, "device_tap", {"ref": minus["ref"], "element": "Minus"})
            await wait_for_text(session, "Count: 1", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # App Bar & Menu
            await open_case(session, "App Bar & Menu")
            await wait_for_text(session, "Open Overflow", timeout=10)
            overflow = await find_one(session, text="Open Overflow")
            await call(session, "device_tap", {"ref": overflow["ref"], "element": "Open Overflow"})
            search_item = await find_one(session, text="Search")
            await call(session, "device_tap", {"ref": search_item["ref"], "element": "Search"})
            await wait_for_text(session, "Last Action: Search", partial=True, timeout=10)
            overflow = await find_one(session, text="Open Overflow")
            await call(session, "device_tap", {"ref": overflow["ref"], "element": "Open Overflow"})
            share_item = await find_one(session, text="Share")
            await call(session, "device_tap", {"ref": share_item["ref"], "element": "Share"})
            await wait_for_text(session, "Last Action: Share", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Navigation Drawer
            await open_case(session, "Navigation Drawer")
            await wait_for_text(session, "Open Drawer", timeout=10)
            open_drawer = await find_one(session, text="Open Drawer")
            await call(session, "device_tap", {"ref": open_drawer["ref"], "element": "Open Drawer"})
            profile = await find_one(session, text="Profile")
            await call(session, "device_tap", {"ref": profile["ref"], "element": "Profile"})
            await wait_for_text(session, "Selected: Profile", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Swipe List
            await open_case(session, "Swipe List")
            await wait_for_text(session, "Reset List", timeout=10)
            removed = False
            for _ in range(2):
                item_result = await call(
                    session,
                    "find_element",
                    {"text": "Swipe Item 1", "refresh_snapshot": True},
                    timeout=20,
                )
                if item_result.get("count", 0) == 0:
                    removed = True
                    break
                swipe_item = item_result["elements"][0]
                await swipe_left_on_element(session, swipe_item)
                removed_result = await wait_for_text(
                    session,
                    "Removed: Swipe Item 1",
                    partial=True,
                    timeout=6,
                )
                if removed_result.get("found"):
                    removed = True
                    break
                still_there = await call(
                    session,
                    "find_element",
                    {"text": "Swipe Item 1", "refresh_snapshot": True},
                    timeout=20,
                )
                if still_there.get("count", 0) == 0:
                    removed = True
                    break
            if not removed:
                raise RuntimeError("Swipe List did not report removing Swipe Item 1")
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            # Chips
            await open_case(session, "Chips")
            await wait_for_text(session, "Show Selection", timeout=10)
            chip_a = await find_one(session, text="Filter A")
            chip_c = await find_one(session, text="Filter C")
            await call(session, "device_tap", {"ref": chip_a["ref"], "element": "Filter A"})
            await call(session, "device_tap", {"ref": chip_c["ref"], "element": "Filter C"})
            apply_btn = await find_one(session, text="Show Selection")
            await call(session, "device_tap", {"ref": apply_btn["ref"], "element": "Show Selection"})
            await wait_for_text(session, "Selected: Filter A, Filter C", partial=True, timeout=10)
            await call(session, "go_back")
            await wait_for_text(session, "Test Cases", timeout=10)

            print("MCP automation test completed successfully")


if __name__ == "__main__":
    anyio.run(run_tests)


def run_tests_sync():
    anyio.run(run_tests)
