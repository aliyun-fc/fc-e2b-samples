"""E2B lifecycle and CDP-driven browser task execution."""

from __future__ import annotations

import asyncio
import re
import time
from urllib.parse import urlparse

from src.core.runs import Run, RunStore
from src.core.settings import Settings


URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
BROWSERTOOL_PORT = 3000
PROCESS_COMPOSE_CONFIG = "/etc/sandbox/config/process-compose.browsertool.yaml"
PROCESS_COMPOSE_LOG = "/tmp/browsertool-process-compose.log"


def task_url(task: str) -> str:
    match = URL_PATTERN.search(task)
    if not match:
        raise ValueError("任务中必须包含完整的 http:// 或 https:// URL。")
    url = match.group(0).rstrip(".,，。；;:：)")
    if urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("仅支持 http(s) URL。")
    return url


class BrowserService:
    def __init__(self, settings: Settings, runs: RunStore) -> None:
        self.settings = settings
        self.runs = runs

    async def execute(self, run: Run) -> None:
        try:
            url = task_url(run.task)
            run.status = "starting"
            await self.runs.emit(run, "sandbox.creating")
            sandbox, template = await asyncio.to_thread(self._create_sandbox)
            run.sandbox = sandbox
            run.sandbox_id = sandbox.sandbox_id
            await self.runs.emit(run, "browser.starting", sandbox_id=run.sandbox_id)
            await asyncio.to_thread(self._start_browsertool, sandbox)
            await self.runs.emit(run, "sandbox.ready", sandbox_id=run.sandbox_id, template=template)
            run.status = "running"
            await self.runs.emit(run, "browser.connecting", url=url)
            title, final_url, screenshot = await asyncio.to_thread(self._navigate_and_capture, sandbox, url)
            run.screenshot = screenshot
            run.result = {"title": title, "url": final_url, "screenshot_url": f"/api/runs/{run.run_id}/screenshot"}
            run.status = "completed"
            await self.runs.emit(run, "browser.screenshot", screenshot_url=run.result["screenshot_url"])
            await self.runs.emit(run, "run.completed", result=run.result)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            await self.runs.emit(run, "run.failed", error=run.error)

    def _create_sandbox(self):
        missing = [
            name
            for name, value in {
                "E2B_API_KEY": self.settings.e2b_api_key,
                "E2B_API_URL": self.settings.e2b_api_url,
                "E2B_DOMAIN": self.settings.e2b_domain,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError("阿里云 E2B 必须配置环境变量：" + ", ".join(missing))
        from e2b import Sandbox, Template

        api_opts = self._e2b_api_opts()
        template = self.settings.e2b_template
        if not template:
            template = Template.build(
                Template().from_image(image=self.settings.e2b_browser_image),
                f"browser-studio-{int(time.time())}",
                cpu_count=2,
                memory_mb=2048,
                **api_opts,
            ).name
        kwargs = {"template": template, "api_key": self.settings.e2b_api_key,
                  "timeout": self.settings.e2b_timeout, "allow_internet_access": True}
        kwargs.update(api_opts)
        return Sandbox.create(**kwargs), template

    def _e2b_api_opts(self) -> dict[str, str]:
        opts = {"api_key": self.settings.e2b_api_key}
        opts["api_url"] = self.settings.e2b_api_url
        opts["domain"] = self.settings.e2b_domain
        return opts

    @staticmethod
    def _start_browsertool(sandbox) -> None:
        """Start the browsertool process supplied by the browser image.

        The E2B browser image exposes CDP only after its process-compose
        configuration is running. This sequence mirrors sandbox-studio's
        browser backend and surfaces a useful log tail when startup fails.
        """
        sandbox.commands.run(
            "install -d -m 1777 /tmp/.X11-unix && rm -f /tmp/.X1-lock && "
            "mkdir -p /run/user/1000/dconf",
            user="root",
        )
        chrome_path = sandbox.commands.run("cat /etc/browsertool/chrome-path", user="root").stdout.strip()
        sandbox.commands.run(
            f"process-compose up -f {PROCESS_COMPOSE_CONFIG} --tui=false --no-server "
            f"> {PROCESS_COMPOSE_LOG} 2>&1",
            envs={"SXBT_BROWSER_CHROMIUM_PATH": chrome_path}, background=True, user="root",
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            status = sandbox.commands.run(
                f"curl -sS -m 2 -o /dev/null -w '%{{http_code}}' "
                f"http://localhost:{BROWSERTOOL_PORT}/health || true",
                user="root",
            ).stdout.strip()
            if status == "200":
                return
            time.sleep(2)
        log = sandbox.commands.run(f"tail -50 {PROCESS_COMPOSE_LOG} || true", user="root").stdout
        raise RuntimeError(f"browsertool 未能在 60 秒内启动：\n{log}")

    def _navigate_and_capture(self, sandbox, url: str) -> tuple[str, str, bytes]:
        from playwright.sync_api import sync_playwright

        host = sandbox.get_host(BROWSERTOOL_PORT)
        token = getattr(sandbox, "_envd_access_token", None)
        if not token:
            raise RuntimeError("E2B 未返回 browsertool 所需的访问令牌。")
        cdp_url = f"wss://{host}/ws/automation"
        with sync_playwright() as playwright:
            browser = self._connect_over_cdp_with_retry(playwright, cdp_url, token)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(750)
            screenshot = page.screenshot(full_page=True, type="png")
            title, final_url = page.title(), page.url
            browser.close()
            return title, final_url, screenshot

    @staticmethod
    def _connect_over_cdp_with_retry(playwright, cdp_url: str, token: str):
        deadline = time.monotonic() + 90
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                return playwright.chromium.connect_over_cdp(
                    cdp_url,
                    headers={"X-Access-Token": token},
                    timeout=10_000,
                )
            except Exception as exc:
                last_error = exc
                time.sleep(3)
        raise RuntimeError(f"browsertool CDP did not become ready: {last_error}")
