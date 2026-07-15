"""Create and manage a browsertool-backed E2B sandbox."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from e2b import Sandbox, Template
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_settings

BROWSERTOOL_PORT = 3000
PROCESS_COMPOSE_CONFIG = "/etc/sandbox/config/process-compose.browsertool.yaml"
PROCESS_COMPOSE_LOG = "/tmp/browsertool-pc.log"


class SandboxManager:
    """Own one E2B sandbox and its authenticated browsertool CDP endpoint."""

    def __init__(self) -> None:
        self._sandbox: Sandbox | None = None
        self._sandbox_id: str | None = None
        self._cdp_url: str | None = None
        self._cdp_headers: dict[str, str] = {}

    def create(self, template_name: str | None = None, idle_timeout: int | None = None) -> dict[str, Any]:
        settings = get_settings()
        if not settings.e2b_api_key:
            raise RuntimeError("E2B_API_KEY is required; copy env.example to .env and configure it.")
        try:
            template = template_name or settings.e2b_template or self._build_template(settings.e2b_browser_image)
            self._sandbox = Sandbox.create(template=template, api_key=settings.e2b_api_key, timeout=idle_timeout or settings.e2b_timeout, allow_internet_access=True)
            self._sandbox_id = self._sandbox.sandbox_id
            self._start_browsertool()
            host = self._sandbox.get_host(BROWSERTOOL_PORT)
            self._cdp_url = f"wss://{host}/ws/automation"
            token = getattr(self._sandbox, "_envd_access_token", None)
            if not token:
                raise RuntimeError("E2B did not provide an access token for the browsertool endpoint.")
            self._cdp_headers = {"X-Access-Token": token}
            self._wait_for_cdp_ready()
        except Exception:
            self.destroy()
            raise
        print(f"E2B sandbox ready: {self._sandbox_id}")
        print("CDP endpoint: [redacted]")
        return self.get_info() or {}

    @staticmethod
    def _build_template(image: str) -> str:
        settings = get_settings()
        name = f"browseruse-e2b-{int(time.time())}"
        print(f"Building E2B template {name} from {image}")
        return Template.build(Template().from_image(image=image), name, api_key=settings.e2b_api_key, cpu_count=2, memory_mb=2048).name

    def _start_browsertool(self) -> None:
        assert self._sandbox is not None
        self._sandbox.commands.run("install -d -m 1777 /tmp/.X11-unix && rm -f /tmp/.X1-lock && mkdir -p /run/user/1000/dconf", user="root")
        chrome_path = self._sandbox.commands.run("cat /etc/browsertool/chrome-path", user="root").stdout.strip()
        self._sandbox.commands.run(f"process-compose up -f {PROCESS_COMPOSE_CONFIG} --tui=false --no-server > {PROCESS_COMPOSE_LOG} 2>&1", envs={"SXBT_BROWSER_CHROMIUM_PATH": chrome_path}, background=True, user="root")
        deadline = time.time() + 60
        while time.time() < deadline:
            status = self._sandbox.commands.run(f"curl -sS -m 2 -o /dev/null -w '%{{http_code}}' http://localhost:{BROWSERTOOL_PORT}/health || true", user="root").stdout.strip()
            if status == "200":
                return
            time.sleep(2)
        log_tail = self._sandbox.commands.run(f"tail -50 {PROCESS_COMPOSE_LOG} || true", user="root").stdout
        raise RuntimeError(f"browsertool did not become ready within 60 seconds:\n{log_tail}")

    def _wait_for_cdp_ready(self) -> None:
        """Wait until browsertool accepts an authenticated Playwright CDP connection.

        The HTTP health endpoint can become available before Chrome's CDP target
        discovery is responsive. BrowserUse has a 15-second CDP startup limit,
        so verify a full CDP client connection before returning the sandbox to it.
        """
        assert self._cdp_url
        deadline = time.time() + 60
        last_error = "no response"
        while time.time() < deadline:
            try:
                # The examples call this synchronous manager from async
                # BrowserUse code. Playwright's sync API therefore needs its
                # own thread rather than the already-running event-loop thread.
                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(self._probe_cdp_with_playwright).result(timeout=10)
                return
            except Exception as exc:
                last_error = str(exc)
            time.sleep(2)
        raise RuntimeError(f"browsertool CDP did not become ready within 60 seconds: {last_error}")

    def _probe_cdp_with_playwright(self) -> None:
        assert self._cdp_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                self._cdp_url, headers=self._cdp_headers, timeout=5000
            )
            browser.close()

    def get_info(self) -> dict[str, Any] | None:
        if not self._sandbox_id or not self._cdp_url:
            return None
        return {"sandbox_id": self._sandbox_id, "cdp_url": self._cdp_url, "cdp_headers": self._cdp_headers.copy(), "status": "RUNNING"}

    def get_sandbox_id(self) -> str | None:
        return self._sandbox_id

    def is_active(self) -> bool:
        return self._sandbox is not None

    def destroy(self) -> None:
        if self._sandbox is not None:
            try:
                self._sandbox.kill()
                print(f"E2B sandbox removed: {self._sandbox_id}")
            finally:
                self._sandbox = None
                self._sandbox_id = self._cdp_url = None
                self._cdp_headers = {}

    def __enter__(self) -> "SandboxManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.destroy()
