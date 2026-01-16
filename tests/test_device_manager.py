import pytest

from src.core.device_manager import DeviceManager, DeviceInfo
from src.core.exceptions import MultipleDevicesError


class DummyDevice:
    @property
    def info(self):
        return {}


def test_resolve_device_id_or_default_uses_single_device(monkeypatch):
    manager = DeviceManager()
    devices = [DeviceInfo(serial="emulator-5554", state="device")]
    monkeypatch.setattr(manager, "list_devices", lambda: devices)

    resolved = manager.resolve_device_id_or_default(None)

    assert resolved == "emulator-5554"


def test_resolve_device_id_or_default_errors_on_multiple_devices(monkeypatch):
    manager = DeviceManager()
    devices = [
        DeviceInfo(serial="device-1", state="device"),
        DeviceInfo(serial="device-2", state="device"),
    ]
    monkeypatch.setattr(manager, "list_devices", lambda: devices)

    with pytest.raises(MultipleDevicesError):
        manager.resolve_device_id_or_default(None)


def test_get_device_uses_single_device_serial(monkeypatch):
    manager = DeviceManager()
    devices = [DeviceInfo(serial="emulator-5554", state="device")]
    monkeypatch.setattr(manager, "list_devices", lambda: devices)

    called = {}

    def fake_connect(device_id):
        called["device_id"] = device_id
        return DummyDevice()

    monkeypatch.setattr("src.core.device_manager.u2.connect", fake_connect)

    with manager.get_device() as device:
        assert device.info == {}

    assert called["device_id"] == "emulator-5554"
