"""Offline lifecycle tests for the in-process sandbox registry."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


class FakeManager:
    """Small stand-in that makes registry tests independent from E2B."""

    next_id = 0

    def __init__(self) -> None:
        type(self).next_id += 1
        self.sandbox_id = f"sandbox-{self.next_id}"
        self.active = False
        self.destroyed = False

    def create(self, **_: object) -> dict[str, object]:
        self.active = True
        return {"sandbox_id": self.sandbox_id, "cdp_url": "wss://example.test/ws", "cdp_headers": {}, "status": "RUNNING"}

    def get_info(self) -> dict[str, object] | None:
        if not self.active:
            return None
        return {"sandbox_id": self.sandbox_id, "cdp_url": "wss://example.test/ws", "cdp_headers": {}, "status": "RUNNING"}

    def get_sandbox_id(self) -> str:
        return self.sandbox_id

    def is_active(self) -> bool:
        return self.active

    def destroy(self) -> None:
        self.active = False
        self.destroyed = True


def load_runner() -> types.ModuleType:
    fake_sandbox_manager = types.ModuleType("sandbox_manager")
    fake_sandbox_manager.SandboxManager = FakeManager
    sys.modules["sandbox_manager"] = fake_sandbox_manager
    spec = importlib.util.spec_from_file_location("runner_under_test", EXAMPLES_DIR / "runner.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeManager.next_id = 0
        self.runner = load_runner()

    def tearDown(self) -> None:
        self.runner.destroy_all_sandboxes()

    def test_reuses_the_same_active_session(self) -> None:
        first = self.runner.create_or_get_sandbox("user", "session", "thread")
        second = self.runner.create_or_get_sandbox("user", "session", "thread")

        self.assertEqual(first["sandbox_id"], second["sandbox_id"])
        self.assertTrue(first["is_new"])
        self.assertFalse(second["is_new"])

    def test_replacing_a_session_invalidates_its_old_id(self) -> None:
        first = self.runner.create_or_get_sandbox("user", "session", "thread")
        replacement = self.runner.create_or_get_sandbox("user", "session", "thread", force_recreate=True)

        self.assertNotEqual(first["sandbox_id"], replacement["sandbox_id"])
        self.assertFalse(self.runner.destroy_sandbox(first["sandbox_id"]))
        self.assertEqual(
            self.runner.get_sandbox_info(sandbox_id=replacement["sandbox_id"])["sandbox_id"],
            replacement["sandbox_id"],
        )

    def test_destroy_removes_the_session(self) -> None:
        sandbox = self.runner.create_or_get_sandbox("user", "session", "thread")

        self.assertTrue(self.runner.destroy_sandbox(sandbox["sandbox_id"]))
        self.assertIsNone(self.runner.get_sandbox_info(sandbox_id=sandbox["sandbox_id"]))


if __name__ == "__main__":
    unittest.main()
