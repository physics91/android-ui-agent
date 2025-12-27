# Repository Guidelines

This repository provides an MCP server for Android UI automation using `uiautomator2`. Follow these guidelines to contribute safely and consistently.

## Project Structure & Module Organization
- `src/`: Core implementation.
  - `src/server.py`: MCP server entry point and tool registration.
  - `src/core/`: Device management, ref system, and exceptions.
  - `src/tools/`: Tool implementations (snapshot, interaction, navigation, waits, watchers, recording, performance).
- `tests/`: Pytest-based tests (integration tests require an Android device).
- `pyproject.toml`: Dependencies, optional dev tools, and build settings.

## Build, Test, and Development Commands
- `pip install -e .`: Install in editable mode for local development.
- `pytest tests/test_server.py -v`: Run test suite (skips integration tests if no device).
- `python src/server.py`: Run the MCP server directly (for local debugging).

## Coding Style & Naming Conventions
- Python 3.10+ with 4-space indentation and PEP 8 conventions.
- Use `snake_case` for functions/variables and `PascalCase` for classes.
- Prefer small, focused functions; avoid duplicated device-resolution logic.
- Optional tooling (declared in `pyproject.toml`): `ruff`, `mypy`, `pytest-cov`.

## Testing Guidelines
- Framework: `pytest`.
- Integration tests require a connected Android device (ADB available).
- Test files live in `tests/` and follow `test_*.py` naming.
- Keep unit tests device-agnostic; gate device-dependent tests with skips.
- Integration tests are marked with `@pytest.mark.integration` and can be skipped via `SKIP_ANDROID_INTEGRATION=1`.

### Running Tests with Android Emulator
1. Start an Android emulator (Android Studio AVD or command line):
   ```bash
   emulator -avd <avd_name>  # or start from Android Studio
   ```
2. Verify ADB connection:
   ```bash
   adb devices  # Should show "emulator-5554 device"
   ```
3. Run integration tests:
   ```bash
   .venv/bin/python -m pytest tests/ -v
   ```
4. Manual tool testing:
   ```bash
   .venv/bin/python -c "
   from src.tools.device import device_list
   from src.tools.snapshot import device_snapshot
   print(device_list())
   print(device_snapshot(device_id='emulator-5554'))
   "
   ```
5. MCP server test (JSON-RPC):
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test"}}}
   {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"device_list","arguments":{}}}' | .venv/bin/python -m src.server
   ```

## Commit & Pull Request Guidelines
- No Git history is present in this checkout, so commit conventions are unspecified.
- Recommended: concise, imperative commit subjects (e.g., “Add snapshot caching”).
- PRs should include: summary, rationale, testing notes, and any device prerequisites.

## Security & Configuration Tips
- Validate device IDs to prevent command injection (see `src/core/device_manager.py`).
- Prefer `defusedxml` for parsing UI hierarchy (required dependency).
- Document any ADB assumptions (device IDs, emulator ports) in PRs.
