"""In-process E2B sandbox reuse keyed by user, session, and thread."""

import atexit
import signal
import threading
from typing import Any

from sandbox_manager import SandboxManager

_instances: dict[tuple[str, str, str], SandboxManager] = {}
_ids: dict[str, tuple[str, str, str]] = {}
_lock = threading.Lock()


def create_or_get_sandbox(user_id: str, session_id: str, thread_id: str, template_name: str | None = None, idle_timeout: int | None = None, force_recreate: bool = False) -> dict[str, Any]:
    """Create a sandbox or return the active sandbox for this session key."""
    if not all((user_id, session_id, thread_id)):
        raise ValueError("user_id, session_id, and thread_id are required")
    key = (user_id, session_id, thread_id)
    with _lock:
        existing = _instances.get(key)
        if existing and existing.is_active() and not force_recreate:
            info = existing.get_info()
            assert info is not None
            info["is_new"] = False
            print(f"Reusing E2B sandbox: {info['sandbox_id']}")
            return info
        if existing:
            # Retire the old ID before creating the replacement. Otherwise a
            # late `destroy_sandbox(old_id)` call could resolve this session
            # key and accidentally destroy the newly-created sandbox.
            old_id = existing.get_sandbox_id()
            if old_id:
                _ids.pop(old_id, None)
            existing.destroy()
        manager = SandboxManager()
        info = manager.create(template_name=template_name, idle_timeout=idle_timeout)
        _instances[key] = manager
        _ids[info["sandbox_id"]] = key
        info["is_new"] = True
        return info


def get_sandbox_info(*, user_id: str | None = None, session_id: str | None = None, thread_id: str | None = None, sandbox_id: str | None = None) -> dict[str, Any] | None:
    with _lock:
        key = _ids.get(sandbox_id) if sandbox_id else (user_id, session_id, thread_id)
        manager = _instances.get(key) if key and all(key) else None
        return manager.get_info() if manager else None


def destroy_sandbox(sandbox_id: str) -> bool:
    with _lock:
        key = _ids.pop(sandbox_id, None)
        manager = _instances.pop(key, None) if key else None
    if not manager:
        return False
    manager.destroy()
    return True


def destroy_all_sandboxes() -> None:
    for sandbox_id in list(_ids):
        destroy_sandbox(sandbox_id)


atexit.register(destroy_all_sandboxes)
try:
    signal.signal(signal.SIGTERM, lambda *_: destroy_all_sandboxes())
except ValueError:
    pass
