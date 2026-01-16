# Recording and Polling Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix gesture coordinate handling, poll interval isolation/validation, and recording limits/error indices without requiring a device for unit tests.

**Architecture:** Store coordinate space metadata per gesture event and resolve it at playback time using the current device screen size. Poll intervals are stored per session (performance) or per device (watchers), validated upfront, and used by background loops without global sharing.

**Tech Stack:** Python 3.10+, pytest

### Task 1: Tests for gesture coordinate metadata + scaling

**Files:**
- Create: `tests/test_recording_coordinates.py`
- Modify: `src/tools/recording.py`

**Step 1: Write the failing tests**

```python
from src.tools import recording


def test_build_gesture_params_sets_coordinate_space():
    params = recording._build_gesture_params(
        "tap",
        x=0.2,
        y=0.4,
        coordinate_space="normalized",
    )
    assert params["coordinate_space"] == "normalized"


def test_build_gesture_params_normalized_flag():
    params = recording._build_gesture_params(
        "tap",
        x=0.2,
        y=0.4,
        normalized=True,
    )
    assert params["coordinate_space"] == "normalized"


def test_apply_coordinate_space_scales_and_clamps():
    params = {
        "x": -0.2,
        "y": 1.2,
        "coordinate_space": "normalized",
    }
    scaled = recording._apply_coordinate_space(params, (100, 200))
    assert scaled["x"] == 0
    assert scaled["y"] == 199
```

**Step 2: Run test to verify it fails**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_coordinates.py`
Expected: FAIL (missing functions/fields)

**Step 3: Write minimal implementation**

```python
# in src/tools/recording.py

def _build_gesture_params(..., coordinate_space: Optional[str] = None, normalized: Optional[bool] = None) -> Dict[str, Any]:
    ...
    if coordinate_space is None and normalized is True:
        coordinate_space = "normalized"
    if coordinate_space is not None:
        params["coordinate_space"] = coordinate_space


def _apply_coordinate_space(params: Dict[str, Any], screen_size: tuple[int, int]) -> Dict[str, int]:
    # scale and clamp if coordinate_space == "normalized"
```

**Step 4: Run test to verify it passes**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_coordinates.py`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_recording_coordinates.py src/tools/recording.py
git commit -m "test: cover gesture coordinate space"
```

### Task 2: Use coordinate space during playback

**Files:**
- Modify: `src/tools/recording.py`
- Modify: `tests/test_recording_coordinates.py`

**Step 1: Write the failing test**

```python
class DummyDevice:
    def __init__(self):
        self.clicked = None
    def click(self, x, y):
        self.clicked = (x, y)


def test_execute_event_uses_normalized_coordinates():
    device = DummyDevice()
    event = recording.GestureEvent(
        type="tap",
        timestamp=0.0,
        params={"x": 0.5, "y": 0.5, "coordinate_space": "normalized"},
    )
    recording._execute_event(device, event, screen_size=(200, 400))
    assert device.clicked == (100, 200)
```

**Step 2: Run test to verify it fails**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_coordinates.py`
Expected: FAIL (signature/behavior mismatch)

**Step 3: Write minimal implementation**

```python
# in src/tools/recording.py

def _execute_event(device, event: "GestureEvent", screen_size: Optional[tuple[int, int]] = None) -> None:
    params = event.params
    params = _apply_coordinate_space(params, screen_size) if screen_size else params
    ...

# in RecordingManager.play_recording
screen_size = device.window_size()
_execute_event(device, event, screen_size=screen_size)
```

**Step 4: Run test to verify it passes**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_coordinates.py`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/recording.py tests/test_recording_coordinates.py
git commit -m "feat: scale normalized gesture coordinates"
```

### Task 3: Recording limit + error index accuracy

**Files:**
- Create: `tests/test_recording_manager.py`
- Modify: `src/tools/recording.py`

**Step 1: Write the failing tests**

```python
from src.tools import recording
from src.tools.recording import RecordingManager, GestureEvent


def test_start_recording_fails_when_limit_reached():
    manager = RecordingManager()
    for i in range(recording.MAX_RECORDINGS):
        manager.start_recording(f"device-{i}")
    assert manager.start_recording("device-extra") is None


def test_play_recording_reports_real_event_index(monkeypatch):
    manager = RecordingManager()
    rec = manager.start_recording("device")
    assert rec is not None
    rec.is_recording = False
    rec.events = [
        GestureEvent(type="tap", timestamp=0.0, params={"x": 1, "y": 1}),
        GestureEvent(type="tap", timestamp=0.1, params={"x": 2, "y": 2}),
    ]

    class DummyDevice:
        def click(self, x, y):
            if x == 2:
                raise RuntimeError("boom")

    class DummyManager:
        def get_device(self, _):
            class _Ctx:
                def __enter__(self_inner):
                    return DummyDevice()
                def __exit__(self_inner, *args):
                    return False
            return _Ctx()

    monkeypatch.setattr("src.tools.recording.get_device_manager", lambda: DummyManager())

    result = manager.play_recording(rec.recording_id, device_id="device")
    assert result["errors"][0]["event_index"] == 1
```

**Step 2: Run test to verify it fails**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_manager.py`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# in src/tools/recording.py
# - enforce MAX_RECORDINGS: if over limit and no completed recordings to evict, return None
# - use enumerate(...) in play_recording to record real event index
```

**Step 4: Run test to verify it passes**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_recording_manager.py`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_recording_manager.py src/tools/recording.py
git commit -m "fix: enforce recording limits and error indices"
```

### Task 4: Poll interval isolation + validation

**Files:**
- Create: `tests/test_poll_intervals.py`
- Modify: `src/tools/performance.py`
- Modify: `src/tools/watcher.py`

**Step 1: Write the failing tests**

```python
import types
import threading
from src.tools.performance import PerformanceMonitor
from src.tools import watcher


def test_performance_monitor_passes_poll_interval(monkeypatch):
    created = {}

    class DummyThread:
        def __init__(self, *args, **kwargs):
            created["args"] = args
            created["kwargs"] = kwargs
        def start(self):
            return None

    monkeypatch.setattr(threading, "Thread", DummyThread)

    monitor = PerformanceMonitor()
    session = monitor.start_monitoring("device", package="pkg", poll_interval=2.5)
    assert session.poll_interval == 2.5
    assert created["kwargs"]["args"][3] == 2.5


def test_watcher_start_rejects_invalid_poll_interval():
    try:
        watcher.watcher_start(poll_interval=0)
        assert False, "expected ValueError"
    except ValueError:
        assert True
```

**Step 2: Run test to verify it fails**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_poll_intervals.py`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# in src/tools/performance.py
# - add poll_interval to MonitoringSession
# - validate poll_interval > 0
# - pass poll_interval into _monitor_loop and use it in sleep

# in src/tools/watcher.py
# - validate poll_interval > 0
# - pass poll_interval into _watcher_loop and use it in sleep
```

**Step 4: Run test to verify it passes**

Run: `SKIP_ANDROID_INTEGRATION=1 .venv/bin/pytest -q tests/test_poll_intervals.py`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_poll_intervals.py src/tools/performance.py src/tools/watcher.py
git commit -m "fix: isolate poll intervals and validate"
```

### Task 5: Update recording API docs

**Files:**
- Modify: `src/tools/recording.py`

**Step 1: Update docstrings**

```python
# in add_gesture_event docstring
# - add coordinate_space/normalized parameter description
```

**Step 2: Commit**

```bash
git add src/tools/recording.py
git commit -m "docs: document coordinate_space for gestures"
```
