"""Device connection manager with multi-device support.

Provides thread-safe device connection management, caching, and multi-device support.
Similar to the original server.py implementation but enhanced for multiple devices.
"""

import contextlib
import logging
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional

import uiautomator2 as u2

from .exceptions import (
    DeviceConnectionError,
    DeviceNotFoundError,
    InvalidDeviceIdError,
)

logger = logging.getLogger(__name__)

# Validation patterns
DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]+$")
MAX_DEVICE_ID_LENGTH = 255
# Memory management
MAX_CACHED_DEVICES = 5
CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class CachedDevice:
    """Cached device with timestamp for TTL management."""
    device: u2.Device
    last_used: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: float = CACHE_TTL_SECONDS) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.last_used > ttl_seconds

    def touch(self):
        """Update last used timestamp."""
        self.last_used = time.time()


@dataclass
class DeviceInfo:
    """Information about a connected device."""

    serial: str
    state: str  # "device", "offline", "unauthorized"
    model: Optional[str] = None
    product: Optional[str] = None
    transport_id: Optional[str] = None

    @property
    def is_available(self) -> bool:
        """Check if device is available for use."""
        return self.state == "device"


def validate_device_id(device_id: Optional[str]) -> bool:
    """Validate device ID format (Command Injection prevention).

    Args:
        device_id: ADB device serial number

    Returns:
        bool: True if valid
    """
    if device_id is None:
        return True  # None means use default device
    if not device_id or not device_id.strip():
        return False
    if len(device_id) > MAX_DEVICE_ID_LENGTH:
        return False
    return DEVICE_ID_PATTERN.match(device_id) is not None


class DeviceManager:
    """Manages Android device connections.

    Features:
    - Thread-safe connection caching
    - Multi-device support with device selection
    - Automatic reconnection on failure
    - Device listing via ADB
    """

    def __init__(self):
        self._cache: Dict[str, CachedDevice] = {}
        self._cache_lock = threading.Lock()
        self._selected_device: Optional[str] = None
        self._selection_lock = threading.Lock()

    def _cleanup_expired_cache(self):
        """Remove expired entries from cache. Must be called with lock held."""
        expired_keys = [
            key for key, cached in self._cache.items()
            if cached.is_expired()
        ]
        for key in expired_keys:
            logger.debug(f"Removing expired cache entry: {key}")
            self._cache.pop(key, None)

    def _evict_oldest_if_needed(self):
        """Evict oldest cache entry if at capacity. Must be called with lock held."""
        if len(self._cache) >= MAX_CACHED_DEVICES:
            # Find oldest entry
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_used
            )
            logger.debug(f"Evicting oldest cache entry: {oldest_key}")
            self._cache.pop(oldest_key, None)

    def list_devices(self) -> List[DeviceInfo]:
        """List all connected Android devices.

        Returns:
            List of DeviceInfo objects
        """
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n")[1:]  # Skip header

            devices = []
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]

                    # Parse additional info
                    model = None
                    product = None
                    transport_id = None
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.split(":")[1]
                        elif part.startswith("product:"):
                            product = part.split(":")[1]
                        elif part.startswith("transport_id:"):
                            transport_id = part.split(":")[1]

                    devices.append(
                        DeviceInfo(
                            serial=serial,
                            state=state,
                            model=model,
                            product=product,
                            transport_id=transport_id,
                        )
                    )

            return devices

        except subprocess.TimeoutExpired:
            logger.error("ADB devices command timed out")
            return []
        except FileNotFoundError:
            logger.error("ADB not found in PATH")
            return []
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    def get_available_devices(self) -> List[DeviceInfo]:
        """Get only available (state=device) devices."""
        return [d for d in self.list_devices() if d.is_available]

    def select_device(self, device_id: str) -> bool:
        """Select a device as the default for subsequent operations.

        Args:
            device_id: Device serial number

        Returns:
            True if device was selected successfully
        """
        if not validate_device_id(device_id):
            raise InvalidDeviceIdError(device_id)

        # Verify device exists
        devices = self.get_available_devices()
        if not any(d.serial == device_id for d in devices):
            raise DeviceNotFoundError(device_id)

        with self._selection_lock:
            self._selected_device = device_id
            logger.info(f"Selected device: {device_id}")
            return True

    def get_selected_device(self) -> Optional[str]:
        """Get the currently selected device ID."""
        with self._selection_lock:
            return self._selected_device

    def resolve_device_id(self, device_id: Optional[str]) -> Optional[str]:
        """Resolve device ID, using selected device if None.

        Args:
            device_id: Explicit device ID or None

        Returns:
            Resolved device ID (may still be None for default)
        """
        if device_id is not None:
            return device_id
        return self.get_selected_device()

    def resolve_device_id_or_default(self, device_id: Optional[str]) -> str:
        """Resolve device ID, falling back to "default" sentinel.

        This keeps a consistent cache key and snapshot namespace when the caller
        doesn't specify or select a device.
        """
        return self.resolve_device_id(device_id) or "default"

    @contextlib.contextmanager
    def get_device(
        self, device_id: Optional[str] = None
    ) -> Generator[u2.Device, None, None]:
        """Get a device connection with caching.

        Args:
            device_id: Device serial (None for default/selected)

        Yields:
            uiautomator2 Device object

        Raises:
            InvalidDeviceIdError: Invalid device ID format
            DeviceConnectionError: Connection failed
            DeviceNotFoundError: No devices available
        """
        # Resolve device ID
        resolved_id = self.resolve_device_id(device_id)

        # Validate
        if not validate_device_id(resolved_id):
            raise InvalidDeviceIdError(resolved_id or "")

        cache_key = resolved_id or "default"

        # Get from cache or connect
        with self._cache_lock:
            # Cleanup expired entries periodically
            self._cleanup_expired_cache()

            if cache_key not in self._cache:
                try:
                    logger.info(f"Connecting to device: {cache_key}")

                    # Check if any device is available when using default
                    if resolved_id is None:
                        devices = self.get_available_devices()
                        if not devices:
                            raise DeviceNotFoundError()

                    # Evict oldest if at capacity
                    self._evict_oldest_if_needed()

                    device = u2.connect(resolved_id)
                    self._cache[cache_key] = CachedDevice(device=device)
                except DeviceNotFoundError:
                    raise
                except Exception as e:
                    logger.error(f"Failed to connect to device: {e}")
                    raise DeviceConnectionError(cache_key, str(e))

            cached = self._cache[cache_key]
            cached.touch()  # Update last used time
            device = cached.device

        # Validate connection and yield
        try:
            device.info  # Ping to verify connection
            yield device
        except Exception as e:
            # Connection lost, invalidate cache
            with self._cache_lock:
                self._cache.pop(cache_key, None)
            logger.warning(f"Device connection lost, cache invalidated: {cache_key}")
            raise DeviceConnectionError(cache_key, f"Connection lost: {e}")

    def get_device_info(self, device_id: Optional[str] = None) -> dict:
        """Get detailed device information.

        Args:
            device_id: Device serial (None for default/selected)

        Returns:
            Dictionary with device details
        """
        with self.get_device(device_id) as device:
            info = device.info
            window = device.window_size()

            return {
                "serial": device.serial,
                "sdk_version": info.get("sdkInt"),
                "android_version": info.get("platformVersion"),
                "product_name": info.get("productName"),
                "screen_size": {"width": window[0], "height": window[1]},
                "display_density": info.get("displaySizeDpX"),
                "orientation": info.get("displayRotation"),
                "screen_on": info.get("screenOn"),
            }

    def disconnect(self, device_id: Optional[str] = None):
        """Disconnect and remove device from cache.

        Args:
            device_id: Device serial (None for default)
        """
        cache_key = device_id or "default"
        with self._cache_lock:
            self._cache.pop(cache_key, None)
        logger.info(f"Disconnected device: {cache_key}")

    def disconnect_all(self):
        """Disconnect all cached devices."""
        with self._cache_lock:
            self._cache.clear()
        logger.info("Disconnected all devices")


# Global singleton
_device_manager: Optional[DeviceManager] = None
_manager_lock = threading.Lock()


def get_device_manager() -> DeviceManager:
    """Get the global DeviceManager instance."""
    global _device_manager
    with _manager_lock:
        if _device_manager is None:
            _device_manager = DeviceManager()
        return _device_manager
