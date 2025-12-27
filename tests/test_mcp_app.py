"""Integration test for MCP automation against the Android test app."""
import os
import pytest


@pytest.mark.integration
def test_mcp_android_app():
    if os.environ.get("SKIP_ANDROID_INTEGRATION") == "1":
        pytest.skip("SKIP_ANDROID_INTEGRATION=1; integration tests skipped")

    import importlib.util
    from pathlib import Path

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "mcp_android_app_test.py"
    spec = importlib.util.spec_from_file_location("mcp_android_app_test", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    # Run the full MCP automation flow; raises on failure.
    module.run_tests_sync()
