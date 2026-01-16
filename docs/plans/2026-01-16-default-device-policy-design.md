# Default Device Resolution Policy

Date: 2026-01-16

## Goal
Fix default-device handling so tools never try to connect to a literal "default" serial, while preserving backward compatibility for snapshot caching. Policy: if no device is selected and no device_id is provided, auto-use the only connected device; if multiple devices are connected, error; if none are connected, keep the existing "no devices" error behavior.

## Decision Summary
- Centralize device resolution in `DeviceManager` to ensure all tools behave consistently.
- Normalize the "default" sentinel to `None` before resolution so it is never passed to `uiautomator2` as a real serial.
- If zero devices: raise `DeviceNotFoundError` (existing behavior).
- If exactly one device: auto-select that device for the operation.
- If multiple devices: raise a new `MultipleDevicesError` with a short list of serials in details.

## Architecture
Introduce a policy-aware resolver inside `DeviceManager` (e.g., `_resolve_device_id_with_policy`) that:
1) Treats `"default"` as `None`.
2) If `device_id` is explicitly provided, validates and returns it.
3) If a device is selected, returns it.
4) Otherwise lists available devices and applies the 0/1/2+ policy.

Both `get_device()` and `resolve_device_id_or_default()` will call this resolver. `get_device()` will use the resolved serial for cache keys and for `u2.connect`, ensuring real device IDs only. `resolve_device_id_or_default()` will return actual serials when available and only fall back to "default" when no devices are connected, preserving snapshot namespace behavior for the empty-device case.

## Error Handling
Add `MultipleDevicesError` (subclass of `DeviceConnectionError`). It will carry details with a short list of device serials to help callers select a device. Existing tool wrappers will pass this through without changes.

## Testing Plan
Add unit tests covering:
- Resolver behavior with 0 devices (DeviceNotFoundError).
- Resolver behavior with 1 device (auto-resolves to that serial).
- Resolver behavior with 2+ devices (MultipleDevicesError).
- Regression test to ensure `get_device()` never attempts `u2.connect("default")` when one device is connected.

## Out of Scope
- Changing public tool signatures.
- Changing snapshot ref semantics.
- New CLI or interactive selection flows.
