"""Shared error handling helpers for tool functions."""
from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable, TypeVar

from ..core import DeviceConnectionError

F = TypeVar("F", bound=Callable[..., object])


def wrap_tool_errors(
    logger,
    message: str,
    *,
    pass_through: Iterable[type[BaseException]] = (),
) -> Callable[[F], F]:
    """Wrap tool errors to log and raise RuntimeError with a consistent message."""
    pass_through_exceptions = tuple(pass_through)

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except DeviceConnectionError:
                raise
            except pass_through_exceptions:
                raise
            except Exception as exc:
                logger.error(f"{message}: {exc}")
                raise RuntimeError(f"{message}: {exc}")

        return wrapper  # type: ignore[return-value]

    return decorator
