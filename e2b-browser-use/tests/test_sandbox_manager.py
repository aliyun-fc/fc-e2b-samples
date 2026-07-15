"""Offline tests for E2B browsertool setup and cleanup behavior."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


class FakeCommands:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def run(self, command: str, **kwargs: object) -> types.SimpleNamespace:
        self.calls.append((command, kwargs))
        if command == "cat /etc/browsertool/chrome-path":
            return types.SimpleNamespace(stdout="/usr/bin/chromium\n")
        if "/health" in command:
            return types.SimpleNamespace(stdout="200")
        return types.SimpleNamespace(stdout="")


class FakeSandbox:
    last: "FakeSandbox | None" = None

    def __init__(self) -> None:
        self.sandbox_id = "sandbox-123"
        self._envd_access_token = "access-token"
        self.commands = FakeCommands()
        self.killed = False

    @classmethod
    def create(cls, **kwargs: object) -> "FakeSandbox":
        instance = cls()
        instance.create_kwargs = kwargs
        cls.last = instance
        return instance

    def get_host(self, port: int) -> str:
        assert port == 3000
        return "sandbox-123.example.test"

    def kill(self) -> None:
        self.killed = True


class FakeTemplate:
    @staticmethod
    def build(*_: object, **__: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(name="temporary-template")

    def from_image(self, *, image: str) -> object:
        return object()


def load_manager(*, token: str = "access-token") -> types.ModuleType:
    class TokenSandbox(FakeSandbox):
        def __init__(self) -> None:
            super().__init__()
            self._envd_access_token = token

    fake_e2b = types.ModuleType("e2b")
    fake_e2b.Sandbox = TokenSandbox
    fake_e2b.Template = FakeTemplate
    fake_config = types.ModuleType("config")
    fake_config.get_settings = lambda: types.SimpleNamespace(
        e2b_api_key="e2b-test-key",
        e2b_template="configured-template",
        e2b_timeout=600,
        e2b_browser_image="unused-image",
    )
    sys.modules["e2b"] = fake_e2b
    sys.modules["config"] = fake_config
    spec = importlib.util.spec_from_file_location("sandbox_manager_under_test", EXAMPLES_DIR / "sandbox_manager.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class ReadyBrowser:
        def close(self) -> None:
            return None

    class ReadyChromium:
        def connect_over_cdp(self, *_: object, **__: object) -> ReadyBrowser:
            return ReadyBrowser()

    class ReadyPlaywright:
        chromium = ReadyChromium()

    class ReadyPlaywrightContext:
        def __enter__(self) -> ReadyPlaywright:
            return ReadyPlaywright()

        def __exit__(self, *_: object) -> None:
            return None

    module.sync_playwright = lambda: ReadyPlaywrightContext()

    return module


class SandboxManagerTests(unittest.TestCase):
    def test_creates_authenticated_cdp_endpoint(self) -> None:
        manager_module = load_manager()
        manager = manager_module.SandboxManager()

        output = io.StringIO()
        with redirect_stdout(output):
            info = manager.create()

        self.assertEqual(info["cdp_url"], "wss://sandbox-123.example.test/ws/automation")
        self.assertEqual(info["cdp_headers"], {"X-Access-Token": "access-token"})
        self.assertNotIn(info["cdp_url"], output.getvalue())
        self.assertNotIn("access-token", output.getvalue())
        sandbox = manager_module.Sandbox.last
        assert sandbox is not None
        self.assertEqual(sandbox.create_kwargs["template"], "configured-template")
        self.assertTrue(any("process-compose up" in call[0] for call in sandbox.commands.calls))

    def test_cleans_up_when_the_access_token_is_missing(self) -> None:
        manager_module = load_manager(token="")
        manager = manager_module.SandboxManager()

        with self.assertRaisesRegex(RuntimeError, "access token"):
            manager.create()

        sandbox = manager_module.Sandbox.last
        assert sandbox is not None
        self.assertTrue(sandbox.killed)
        self.assertFalse(manager.is_active())

    def test_waits_for_an_authenticated_playwright_cdp_connection(self) -> None:
        manager_module = load_manager()
        connect_calls: list[dict[str, object]] = []

        class Browser:
            def close(self) -> None:
                return None

        class Chromium:
            def connect_over_cdp(self, _url: str, **kwargs: object) -> Browser:
                connect_calls.append(kwargs)
                return Browser()

        class Playwright:
            chromium = Chromium()

        class PlaywrightContext:
            def __enter__(self):
                return Playwright()

            def __exit__(self, *_: object) -> None:
                return None

        manager_module.sync_playwright = lambda: PlaywrightContext()
        manager = manager_module.SandboxManager()
        manager._cdp_url = "wss://sandbox.example.test/ws/automation"
        manager._cdp_headers = {"X-Access-Token": "access-token"}

        manager._wait_for_cdp_ready()

        self.assertEqual(connect_calls[0]["headers"], manager._cdp_headers)
        self.assertEqual(connect_calls[0]["timeout"], 5000)


if __name__ == "__main__":
    unittest.main()
