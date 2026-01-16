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
