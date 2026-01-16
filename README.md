# Android UI Agent MCP Server

uiautomator2 기반 Android UI 자동화를 MCP 도구로 제공합니다.

## Quickstart

```bash
cd /home/physics91/dev/android-tester
pip install -e .
adb devices
python src/server.py
```

MCP 클라이언트 설정 예시 (Claude Code):

```json
{
  "mcpServers": {
    "android-ui-agent": {
      "command": "python",
      "args": ["/home/physics91/dev/android-tester/src/server.py"]
    }
  }
}
```

기본 사용 흐름:
1. `device_list`로 디바이스 확인
2. `device_snapshot`으로 UI 스냅샷/refs 획득
3. `device_tap`, `device_type` 등으로 상호작용

## MCP 툴 목록

- Device: `device_list`(연결 목록), `device_select`(기본 지정), `device_info`(정보), `device_unlock`(잠금 해제)
- Snapshot & Find: `device_snapshot`(UI 스냅샷+refs), `screenshot`(base64 PNG), `find_element`(조건 검색)
- Interaction: `device_tap`, `device_double_tap`, `device_long_press`, `device_type`, `device_swipe`, `clear_text`
- Navigation: `app_start`, `app_stop`, `app_current`, `go_back`, `go_home`, `press_key`, `open_notification`, `open_quick_settings`, `set_orientation`
- Wait: `wait_seconds`, `wait_for_element`, `wait_for_text`, `wait_for_activity`, `wait_for_element_gone`
- Watchers: `watcher_add`, `watcher_remove`, `watcher_list`, `watcher_start`, `watcher_stop`, `watcher_trigger_once`
- Recording: `start_gesture_recording`, `add_gesture_event`, `stop_gesture_recording`, `play_gesture_recording`, `list_gesture_recordings`, `export_gesture_recording`, `import_gesture_recording`, `delete_gesture_recording`
- Performance: `get_performance_metrics`, `start_performance_monitor`, `stop_performance_monitor`

## 의존성

- `mcp>=1.0.0` - MCP 서버 프레임워크
- `uiautomator2>=3.4.0` - Android UI 자동화
- `Pillow>=10.0.0` - 이미지 처리

## 테스트

```bash
# Android 디바이스 연결 필요
pytest tests/test_server.py -v
```
