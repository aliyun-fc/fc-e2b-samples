"""Safe, human-readable runtime events for the interactive demo."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
import re
from typing import Any


EventSink = Callable[[str, Mapping[str, Any]], None]

SENSITIVE_KEYS = {"api_key", "authorization", "token", "cdp_url", "headers"}
WEBSOCKET_URL = re.compile(r"wss?://[^\s'\"]+")


def redact_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Remove connection credentials and endpoints before they reach stdout."""
    return {key: _redact_value(key, value) for key, value in fields.items()}


def redact_text(value: str) -> str:
    """Mask a CDP endpoint that may be embedded in an SDK error message."""
    return WEBSOCKET_URL.sub("[redacted websocket url]", value)


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in SENSITIVE_KEYS:
        return "[redacted]"
    if isinstance(value, Mapping):
        return redact_fields(value)
    if isinstance(value, str):
        return redact_text(value)
    return value


class ConsoleEventLogger:
    """Print one timestamped event per line without credentials."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def __call__(self, name: str, fields: Mapping[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        payload = redact_fields(fields or {})
        details = " ".join(f"{key}={value}" for key, value in payload.items())
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {name}" + (f" | {details}" if details else ""), flush=True)


def emit(sink: EventSink | None, name: str, **fields: Any) -> None:
    """Send an event when observability is enabled."""
    if sink is not None:
        sink(name, fields)
