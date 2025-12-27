"""Tests for the Playwright-style ref system.

Unit tests for ElementInfo, Snapshot, and SnapshotManager.
"""
import time

import pytest

# NOTE: Do not mock uiautomator2 globally here.
# Global mocks leak into integration tests in tests/test_server.py.

from src.core.ref_system import (
    ElementInfo,
    Snapshot,
    SnapshotManager,
    get_snapshot_manager,
)
from src.core.exceptions import RefNotFoundError, StaleRefError


# === Sample XML data for testing ===

SAMPLE_UI_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.app" content-desc="" checkable="false" checked="false" clickable="false" enabled="true" focusable="false" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[0,0][1080,2400]">
    <node index="0" text="Login" resource-id="com.example.app:id/login_button" class="android.widget.Button" package="com.example.app" content-desc="Login button" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[100,200][300,280]" />
    <node index="1" text="" resource-id="com.example.app:id/email_input" class="android.widget.EditText" package="com.example.app" content-desc="Email" checkable="false" checked="false" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="true" password="false" selected="false" bounds="[50,300][1030,400]" />
    <node index="2" text="" resource-id="com.example.app:id/password_input" class="android.widget.EditText" package="com.example.app" content-desc="Password" checkable="false" checked="false" clickable="true" enabled="false" focusable="true" focused="false" scrollable="false" long-clickable="false" password="true" selected="false" bounds="[50,420][1030,520]" />
    <node index="3" text="Remember me" resource-id="com.example.app:id/remember_checkbox" class="android.widget.CheckBox" package="com.example.app" content-desc="" checkable="true" checked="true" clickable="true" enabled="true" focusable="true" focused="false" scrollable="false" long-clickable="false" password="false" selected="false" bounds="[50,540][300,600]" />
  </node>
</hierarchy>
"""

SIMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Hello" class="android.widget.TextView" bounds="[100,100][200,150]" clickable="true" enabled="true" />
</hierarchy>
"""


# === ElementInfo Tests ===


class TestElementInfo:
    """Tests for ElementInfo dataclass."""

    def test_center_calculation(self):
        """Center is calculated correctly from bounds."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(100, 200, 300, 280),
        )
        assert element.center == (200, 240)

    def test_width_calculation(self):
        """Width is calculated correctly from bounds."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(100, 200, 300, 280),
        )
        assert element.width == 200

    def test_height_calculation(self):
        """Height is calculated correctly from bounds."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(100, 200, 300, 280),
        )
        assert element.height == 80

    def test_to_dict(self):
        """to_dict returns expected structure."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(100, 200, 300, 280),
            text="Login",
            clickable=True,
            enabled=True,
        )
        result = element.to_dict()

        assert result["class"] == "android.widget.Button"
        assert result["text"] == "Login"
        assert result["bounds"] == [100, 200, 300, 280]
        assert result["center"] == [200, 240]
        assert result["clickable"] is True
        assert result["enabled"] is True

    def test_matches_exact_text(self):
        """matches with exact text works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            text="Login",
        )
        assert element.matches(text="Login") is True
        assert element.matches(text="Logout") is False

    def test_matches_text_contains(self):
        """matches with text_contains works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            text="Login to continue",
        )
        assert element.matches(text_contains="Login") is True
        assert element.matches(text_contains="continue") is True
        assert element.matches(text_contains="Logout") is False

    def test_matches_resource_id(self):
        """matches with resource_id works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            resource_id="com.app:id/login_btn",
        )
        assert element.matches(resource_id="com.app:id/login_btn") is True
        assert element.matches(resource_id_contains="login") is True
        assert element.matches(resource_id="other") is False

    def test_matches_class_name(self):
        """matches with class_name works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
        )
        assert element.matches(class_name="android.widget.Button") is True
        assert element.matches(class_name="android.widget.TextView") is False

    def test_matches_clickable_filter(self):
        """matches with clickable filter works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            clickable=True,
        )
        assert element.matches(clickable=True) is True
        assert element.matches(clickable=False) is False

    def test_matches_multiple_criteria(self):
        """matches with multiple criteria works."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            text="Login",
            clickable=True,
            enabled=True,
        )
        assert element.matches(text="Login", clickable=True, enabled=True) is True
        assert element.matches(text="Login", clickable=False) is False


# === Snapshot Tests ===


class TestSnapshot:
    """Tests for Snapshot dataclass."""

    def test_is_stale_fresh(self):
        """Fresh snapshot is not stale."""
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=time.time(),
            screen_size=(1080, 2400),
        )
        assert snapshot.is_stale(max_age_seconds=30.0) is False

    def test_is_stale_old(self):
        """Old snapshot is stale."""
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=time.time() - 60,  # 60 seconds ago
            screen_size=(1080, 2400),
        )
        assert snapshot.is_stale(max_age_seconds=30.0) is True

    def test_age_seconds(self):
        """age_seconds returns correct value."""
        timestamp = time.time() - 5
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=timestamp,
            screen_size=(1080, 2400),
        )
        assert 4.9 < snapshot.age_seconds < 6.0

    def test_get_element(self):
        """get_element returns element by ref."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
        )
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=time.time(),
            screen_size=(1080, 2400),
            refs={"e0": element},
        )
        assert snapshot.get_element("e0") == element
        assert snapshot.get_element("e99") is None

    def test_find_elements(self):
        """find_elements returns matching elements."""
        btn1 = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(0, 0, 100, 100),
            text="OK",
            clickable=True,
        )
        btn2 = ElementInfo(
            ref="e1",
            class_name="android.widget.Button",
            bounds=(0, 100, 100, 200),
            text="Cancel",
            clickable=True,
        )
        text = ElementInfo(
            ref="e2",
            class_name="android.widget.TextView",
            bounds=(0, 200, 100, 300),
            text="Info",
            clickable=False,
        )
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=time.time(),
            screen_size=(1080, 2400),
            refs={"e0": btn1, "e1": btn2, "e2": text},
        )

        # Find all clickable
        clickable = snapshot.find_elements(clickable=True)
        assert len(clickable) == 2

        # Find by class
        buttons = snapshot.find_elements(class_name="android.widget.Button")
        assert len(buttons) == 2

        # Find by text
        ok_btn = snapshot.find_elements(text="OK")
        assert len(ok_btn) == 1
        assert ok_btn[0].ref == "e0"

    def test_to_dict(self):
        """to_dict returns expected structure."""
        element = ElementInfo(
            ref="e0",
            class_name="android.widget.Button",
            bounds=(100, 200, 300, 280),
            text="Login",
        )
        snapshot = Snapshot(
            snapshot_id="test_123",
            device_id="default",
            package="com.app",
            activity=".MainActivity",
            timestamp=time.time(),
            screen_size=(1080, 2400),
            refs={"e0": element},
        )
        result = snapshot.to_dict()

        assert result["snapshot_id"] == "test_123"
        assert result["url"] == "com.app/.MainActivity"
        assert result["screen_size"] == {"width": 1080, "height": 2400}
        assert result["element_count"] == 1
        assert "e0" in result["refs"]


# === SnapshotManager Tests ===


class TestSnapshotManager:
    """Tests for SnapshotManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh SnapshotManager."""
        return SnapshotManager(max_snapshots_per_device=3, default_stale_seconds=30.0)

    def test_create_snapshot_parses_xml(self, manager):
        """create_snapshot parses XML and creates refs."""
        snapshot = manager.create_snapshot(
            device_id="test_device",
            xml_content=SAMPLE_UI_XML,
            package="com.example.app",
            activity=".LoginActivity",
            screen_size=(1080, 2400),
        )

        assert snapshot.device_id == "test_device"
        assert snapshot.package == "com.example.app"
        assert len(snapshot.refs) >= 4  # FrameLayout + 4 children

    def test_create_snapshot_assigns_sequential_refs(self, manager):
        """Refs are assigned sequentially (e0, e1, e2...)."""
        snapshot = manager.create_snapshot(
            device_id="test_device",
            xml_content=SAMPLE_UI_XML,
            package="com.example.app",
            activity=".LoginActivity",
            screen_size=(1080, 2400),
        )

        refs = list(snapshot.refs.keys())
        assert "e0" in refs
        assert "e1" in refs

    def test_create_snapshot_extracts_element_properties(self, manager):
        """Element properties are extracted from XML."""
        snapshot = manager.create_snapshot(
            device_id="test_device",
            xml_content=SAMPLE_UI_XML,
            package="com.example.app",
            activity=".LoginActivity",
            screen_size=(1080, 2400),
        )

        # Find login button
        login_btn = None
        for elem in snapshot.refs.values():
            if elem.text == "Login":
                login_btn = elem
                break

        assert login_btn is not None
        assert login_btn.class_name == "android.widget.Button"
        assert login_btn.resource_id == "com.example.app:id/login_button"
        assert login_btn.content_desc == "Login button"
        assert login_btn.clickable is True
        assert login_btn.bounds == (100, 200, 300, 280)

    def test_get_current_snapshot(self, manager):
        """get_current_snapshot returns most recent snapshot."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity1",
            screen_size=(1080, 2400),
        )
        snapshot2 = manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity2",
            screen_size=(1080, 2400),
        )

        current = manager.get_current_snapshot("test_device")
        assert current.snapshot_id == snapshot2.snapshot_id
        assert current.activity == ".Activity2"

    def test_resolve_ref_success(self, manager):
        """resolve_ref returns element for valid ref."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )

        element = manager.resolve_ref("test_device", "e0", validate_staleness=False)
        assert element.text == "Hello"

    def test_resolve_ref_not_found(self, manager):
        """resolve_ref raises RefNotFoundError for invalid ref."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )

        with pytest.raises(RefNotFoundError):
            manager.resolve_ref("test_device", "e99", validate_staleness=False)

    def test_resolve_ref_no_snapshot(self, manager):
        """resolve_ref raises RefNotFoundError when no snapshot exists."""
        with pytest.raises(RefNotFoundError):
            manager.resolve_ref("nonexistent_device", "e0")

    def test_resolve_ref_stale(self, manager):
        """resolve_ref raises StaleRefError for old snapshot."""
        # Create snapshot with old timestamp
        snapshot = manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )
        # Manually make it old
        snapshot.timestamp = time.time() - 60

        with pytest.raises(StaleRefError):
            manager.resolve_ref("test_device", "e0", validate_staleness=True, max_stale_seconds=30)

    def test_get_position(self, manager):
        """get_position returns center coordinates."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )

        # Element bounds: [100,100][200,150] -> center: (150, 125)
        x, y = manager.get_position("test_device", "e0")
        assert x == 150
        assert y == 125

    def test_find_elements(self, manager):
        """find_elements returns matching elements from current snapshot."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SAMPLE_UI_XML,
            package="com.example.app",
            activity=".LoginActivity",
            screen_size=(1080, 2400),
        )

        # Find clickable elements
        clickable = manager.find_elements("test_device", clickable=True)
        assert len(clickable) >= 3  # Button, EditTexts, CheckBox

        # Find by text
        login = manager.find_elements("test_device", text="Login")
        assert len(login) == 1

    def test_max_snapshots_limit(self, manager):
        """Old snapshots are removed when limit is exceeded."""
        # Create more snapshots than limit (3)
        for i in range(5):
            manager.create_snapshot(
                device_id="test_device",
                xml_content=SIMPLE_XML,
                package="com.app",
                activity=f".Activity{i}",
                screen_size=(1080, 2400),
            )

        # Should only keep 3 most recent
        with manager._lock:
            assert len(manager._snapshots["test_device"]) == 3

    def test_invalidate(self, manager):
        """invalidate removes all snapshots for device."""
        manager.create_snapshot(
            device_id="test_device",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )

        manager.invalidate("test_device")

        assert manager.get_current_snapshot("test_device") is None

    def test_clear_all(self, manager):
        """clear_all removes all snapshots for all devices."""
        manager.create_snapshot(
            device_id="device1",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )
        manager.create_snapshot(
            device_id="device2",
            xml_content=SIMPLE_XML,
            package="com.app",
            activity=".Activity",
            screen_size=(1080, 2400),
        )

        manager.clear_all()

        assert manager.get_current_snapshot("device1") is None
        assert manager.get_current_snapshot("device2") is None


# === Global Singleton Tests ===


class TestGlobalSnapshotManager:
    """Tests for global singleton."""

    def test_get_snapshot_manager_returns_singleton(self):
        """get_snapshot_manager returns the same instance."""
        manager1 = get_snapshot_manager()
        manager2 = get_snapshot_manager()
        assert manager1 is manager2

    def test_get_snapshot_manager_is_snapshot_manager(self):
        """get_snapshot_manager returns SnapshotManager instance."""
        manager = get_snapshot_manager()
        assert isinstance(manager, SnapshotManager)
