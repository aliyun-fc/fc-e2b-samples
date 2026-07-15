"""Regression tests for the observable CLI event format."""

import unittest
import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from main import run_query
from runtime_events import redact_fields, redact_text


class RuntimeEventsTest(unittest.TestCase):
    def test_redacts_browser_connection_secrets(self) -> None:
        self.assertEqual(
            redact_fields(
                {
                    "sandbox_id": "sbx-123",
                    "cdp_url": "wss://private.example/ws/automation",
                    "token": "secret",
                    "headers": {"X-Access-Token": "secret"},
                }
            ),
            {
                "sandbox_id": "sbx-123",
                "cdp_url": "[redacted]",
                "token": "[redacted]",
                "headers": "[redacted]",
            },
        )

    def test_streamed_final_model_message_is_returned(self) -> None:
        class Message:
            content = "已导航到 example.com，页面标题: Example Domain"
            tool_calls = []

        class FakeAgent:
            def stream(self, _input, stream_mode):
                self.assertEqual(stream_mode, "updates")
                yield {"model": {"messages": [Message()]}}

            def assertEqual(self, left, right):
                if left != right:
                    raise AssertionError(f"{left!r} != {right!r}")

        self.assertEqual(
            run_query(FakeAgent(), "导航到 https://example.com", verbose=False),
            Message.content,
        )

    def test_redacts_websocket_url_embedded_in_error_text(self) -> None:
        self.assertEqual(
            redact_text("connect failed: wss://private.example/ws/automation"),
            "connect failed: [redacted websocket url]",
        )


if __name__ == "__main__":
    unittest.main()
