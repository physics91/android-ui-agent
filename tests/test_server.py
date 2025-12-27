"""Tests for Android UI Agent MCP Server

Note: Integration tests require a connected Android device or emulator.
Run with: pytest tests/test_server.py -v
"""
import base64
import xml.etree.ElementTree as ET

import pytest


# === PNG 상수 ===
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


# === Fixtures ===

@pytest.fixture
def connected_device():
    """Check if an Android device is connected"""
    import subprocess
    from unittest.mock import MagicMock
    import os

    if os.environ.get("SKIP_ANDROID_INTEGRATION") == "1":
        pytest.skip("SKIP_ANDROID_INTEGRATION=1; integration tests skipped")

    try:
        import uiautomator2 as u2
    except Exception:
        pytest.skip("uiautomator2 not available; integration tests skipped")
    if isinstance(u2, MagicMock):
        pytest.skip("uiautomator2 is mocked; integration tests require a real device")

    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    # Filter out header and empty lines
    devices = [line for line in lines[1:] if line.strip() and 'device' in line]
    if not devices:
        pytest.skip("No Android device connected")
    return None  # Use default device


# === Unit Tests: Input Validation ===

class TestValidateDeviceId:
    """Tests for validate_device_id function"""

    def test_none_is_valid(self):
        """None은 유효 (기본 디바이스 사용)"""
        from src.server import validate_device_id
        assert validate_device_id(None) is True

    def test_valid_emulator_id(self):
        """에뮬레이터 ID 형식"""
        from src.server import validate_device_id
        assert validate_device_id("emulator-5554") is True

    def test_valid_ip_port(self):
        """IP:PORT 형식"""
        from src.server import validate_device_id
        assert validate_device_id("192.168.1.100:5555") is True

    def test_valid_serial(self):
        """시리얼 번호 형식"""
        from src.server import validate_device_id
        assert validate_device_id("ABC123DEF456") is True

    def test_empty_string_is_invalid(self):
        """빈 문자열 거부"""
        from src.server import validate_device_id
        assert validate_device_id("") is False

    def test_whitespace_only_is_invalid(self):
        """공백만 있는 문자열 거부"""
        from src.server import validate_device_id
        assert validate_device_id("   ") is False

    def test_too_long_is_invalid(self):
        """255자 초과 거부"""
        from src.server import validate_device_id
        assert validate_device_id("a" * 256) is False

    def test_command_injection_is_invalid(self):
        """Command Injection 시도 거부"""
        from src.server import validate_device_id
        malicious_inputs = [
            "device; rm -rf /",
            "device && cat /etc/passwd",
            "device | ls",
            "device`whoami`",
            "device$(cat /etc/passwd)",
            "../../../etc/passwd",
            "device\nmalicious",
        ]
        for malicious_id in malicious_inputs:
            assert validate_device_id(malicious_id) is False, f"Should reject: {malicious_id}"


# === Unit Tests: Error Handling ===

class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_device_id_raises_valueerror(self):
        """잘못된 device_id는 ValueError 발생"""
        from src.server import capture_screenshot
        with pytest.raises(ValueError, match="Invalid device_id format"):
            capture_screenshot(device_id="invalid;command")

    def test_invalid_device_id_in_hierarchy(self):
        """dump_ui_hierarchy도 device_id 검증"""
        from src.server import dump_ui_hierarchy
        with pytest.raises(ValueError, match="Invalid device_id format"):
            dump_ui_hierarchy(device_id="invalid|command")


# === Integration Tests: Screenshot ===

@pytest.mark.integration
class TestCaptureScreenshot:
    """Tests for capture_screenshot tool (requires connected device)"""

    def test_returns_string(self, connected_device):
        """스크린샷 결과는 문자열"""
        from src.server import capture_screenshot
        result = capture_screenshot()
        assert isinstance(result, str)

    def test_returns_valid_base64(self, connected_device):
        """스크린샷이 유효한 base64 문자열인지 확인"""
        from src.server import capture_screenshot
        result = capture_screenshot()

        # base64 디코딩 가능해야 함
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_returns_png_image(self, connected_device):
        """스크린샷이 PNG 이미지인지 확인"""
        from src.server import capture_screenshot
        result = capture_screenshot()

        decoded = base64.b64decode(result)
        assert decoded[:8] == PNG_SIGNATURE, "Should be a valid PNG image"


# === Integration Tests: UI Hierarchy ===

@pytest.mark.integration
class TestDumpUiHierarchy:
    """Tests for dump_ui_hierarchy tool (requires connected device)"""

    def test_returns_string(self, connected_device):
        """UI hierarchy 결과는 문자열"""
        from src.server import dump_ui_hierarchy
        result = dump_ui_hierarchy()
        assert isinstance(result, str)

    def test_returns_valid_xml(self, connected_device):
        """UI hierarchy가 유효한 XML인지 확인"""
        from src.server import dump_ui_hierarchy
        result = dump_ui_hierarchy()

        # XML 파싱 가능해야 함
        root = ET.fromstring(result)
        assert root is not None

    def test_xml_has_hierarchy_root(self, connected_device):
        """XML 루트가 hierarchy인지 확인"""
        from src.server import dump_ui_hierarchy
        result = dump_ui_hierarchy()

        root = ET.fromstring(result)
        assert root.tag == 'hierarchy', "Root element should be 'hierarchy'"

    def test_xml_contains_nodes(self, connected_device):
        """XML에 UI 노드가 포함되어 있는지 확인"""
        from src.server import dump_ui_hierarchy
        result = dump_ui_hierarchy()

        root = ET.fromstring(result)
        children = list(root)
        assert len(children) > 0, "Should have at least one UI node"

    def test_pretty_parameter_accepted(self, connected_device):
        """pretty 파라미터가 정상 동작"""
        from src.server import dump_ui_hierarchy
        result_pretty = dump_ui_hierarchy(pretty=True)
        result_default = dump_ui_hierarchy(pretty=False)

        # 둘 다 유효한 XML 반환
        root_pretty = ET.fromstring(result_pretty)
        root_default = ET.fromstring(result_default)
        assert root_pretty.tag == 'hierarchy'
        assert root_default.tag == 'hierarchy'


# === Unit Tests: Device Caching ===

class TestDeviceCaching:
    """Tests for device connection caching"""

    def test_cache_is_thread_safe(self):
        """캐시가 스레드 안전한지 확인"""
        from src.server import _cache_lock
        import threading

        # Lock이 존재하고 threading.Lock 타입인지 확인
        assert _cache_lock is not None
        assert isinstance(_cache_lock, type(threading.Lock()))
