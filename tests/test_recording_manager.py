from src.tools import recording
from src.tools.recording import RecordingManager, GestureEvent


def test_start_recording_fails_when_limit_reached():
    manager = RecordingManager()
    for i in range(recording.MAX_RECORDINGS):
        rec = manager.start_recording(f"device-{i}")
        assert rec is not None
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
            raise RuntimeError("boom")

        def window_size(self):
            return (100, 100)

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
    assert len(result["errors"]) == 2
    assert result["errors"][1]["event_index"] == 1
