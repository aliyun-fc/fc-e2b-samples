"""Create, connect to, and destroy an E2B browser sandbox."""

import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from e2b import Sandbox, Template

from runtime_events import EventSink, emit


load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

BROWSERTOOL_PORT = 3000
PROCESS_COMPOSE_CONFIG = "/etc/sandbox/config/process-compose.browsertool.yaml"
PROCESS_COMPOSE_LOG = "/tmp/browsertool-process-compose.log"
DEFAULT_BROWSER_IMAGE = "fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.32"


class SandboxManager:
    """Manage one E2B sandbox and its browsertool CDP endpoint."""

    def __init__(self, event_sink: EventSink | None = None) -> None:
        self._sandbox: Optional[Sandbox] = None
        self._template: Optional[str] = None
        self._event_sink = event_sink

    def set_event_sink(self, event_sink: EventSink | None) -> None:
        self._event_sink = event_sink

    def create(self, idle_timeout: Optional[int] = None) -> dict[str, str]:
        """Create a sandbox, start browsertool, and return its CDP endpoint."""
        if self._sandbox is not None:
            emit(self._event_sink, "sandbox.reused", sandbox_id=self._sandbox.sandbox_id)
            return self.get_info()

        api_opts = self._alibaba_e2b_api_opts()
        api_key = api_opts["api_key"]

        emit(self._event_sink, "template.build.started")
        template = self._build_template(api_key)
        self._template = template
        emit(self._event_sink, "template.build.completed", template=template)

        timeout = idle_timeout or int(os.getenv("E2B_TIMEOUT", "600"))
        try:
            emit(self._event_sink, "sandbox.create.started", template=template, timeout=timeout)
            self._sandbox = Sandbox.create(
                template=template,
                timeout=timeout,
                allow_internet_access=True,
                **api_opts,
            )
            emit(self._event_sink, "sandbox.create.completed", sandbox_id=self._sandbox.sandbox_id)
            self._start_browsertool()
            emit(self._event_sink, "browser.ready", sandbox_id=self._sandbox.sandbox_id)
            return self.get_info()
        except Exception as exc:
            emit(self._event_sink, "sandbox.create.failed", error=str(exc))
            self.destroy()
            raise

    def get_info(self) -> dict[str, str]:
        """Return the active sandbox ID and authenticated CDP endpoint."""
        if self._sandbox is None:
            raise RuntimeError("没有活动的 sandbox，请先创建")
        return {
            "sandbox_id": self._sandbox.sandbox_id,
            "cdp_url": self.get_cdp_url(),
            "template": self._template or "",
        }

    def get_cdp_url(self) -> str:
        """Return the public browsertool WebSocket URL for the active sandbox."""
        if self._sandbox is None:
            raise RuntimeError("没有活动的 sandbox，请先创建")
        return f"wss://{self._sandbox.get_host(BROWSERTOOL_PORT)}/ws/automation"

    def get_cdp_headers(self) -> dict[str, str]:
        """Return headers required to authenticate a CDP WebSocket connection."""
        if self._sandbox is None:
            raise RuntimeError("没有活动的 sandbox，请先创建")
        token = getattr(self._sandbox, "_envd_access_token", None)
        return {"X-Access-Token": token} if token else {}

    def destroy(self) -> str:
        """Destroy the active E2B sandbox and clear local state."""
        sandbox, self._sandbox = self._sandbox, None
        self._template = None
        if sandbox is None:
            return "没有活动的 sandbox"
        sandbox_id = sandbox.sandbox_id
        try:
            emit(self._event_sink, "sandbox.destroy.started", sandbox_id=sandbox_id)
            sandbox.kill()
            emit(self._event_sink, "sandbox.destroy.completed", sandbox_id=sandbox_id)
            return f"Sandbox 已销毁: {sandbox_id}"
        except Exception as exc:
            emit(self._event_sink, "sandbox.destroy.failed", sandbox_id=sandbox_id, error=str(exc))
            return f"销毁 Sandbox 时出错: {exc}"

    def is_active(self) -> bool:
        return self._sandbox is not None

    def _build_template(self, api_key: str) -> str:
        """Build a browser template from E2B_BROWSER_IMAGE."""
        image = os.getenv("E2B_BROWSER_IMAGE", DEFAULT_BROWSER_IMAGE)
        template_name = f"langchain-browser-{int(time.time())}"
        emit(self._event_sink, "template.build.image_selected", image=image)
        build_info = Template.build(
            Template().from_image(image=image),
            template_name,
            **self._alibaba_e2b_api_opts(),
            cpu_count=2,
            memory_mb=2048,
        )
        return build_info.name

    @staticmethod
    def _alibaba_e2b_api_opts() -> dict[str, str]:
        values = {
            "api_key": os.getenv("E2B_API_KEY", "").strip(),
            "api_url": os.getenv("E2B_API_URL", "").strip(),
            "domain": os.getenv("E2B_DOMAIN", "").strip(),
        }
        missing = [name for key, name in {
            "api_key": "E2B_API_KEY",
            "api_url": "E2B_API_URL",
            "domain": "E2B_DOMAIN",
        }.items() if not values[key]]
        if missing:
            raise RuntimeError("阿里云 E2B 必须设置环境变量: " + ", ".join(missing))
        return values

    def _start_browsertool(self) -> None:
        """Start browsertool in the sandbox and wait until its health check succeeds."""
        if self._sandbox is None:
            raise RuntimeError("sandbox 尚未创建")
        sandbox = self._sandbox
        sandbox.commands.run(
            "install -d -m 1777 /tmp/.X11-unix && rm -f /tmp/.X1-lock && "
            "mkdir -p /run/user/1000/dconf",
            user="root",
        )
        emit(self._event_sink, "browser.start.started")
        chrome_path = sandbox.commands.run(
            "cat /etc/browsertool/chrome-path", user="root"
        ).stdout.strip()
        sandbox.commands.run(
            f"process-compose up -f {PROCESS_COMPOSE_CONFIG} --tui=false --no-server "
            f"> {PROCESS_COMPOSE_LOG} 2>&1",
            envs={"SXBT_BROWSER_CHROMIUM_PATH": chrome_path},
            background=True,
            user="root",
        )

        deadline = time.time() + 60
        while time.time() < deadline:
            result = sandbox.commands.run(
                f"curl -sS -m 2 -o /dev/null -w '%{{http_code}}' "
                f"http://localhost:{BROWSERTOOL_PORT}/health || true",
                user="root",
            )
            if result.stdout.strip() == "200":
                emit(self._event_sink, "browser.health_check.passed")
                return
            time.sleep(2)

        log = sandbox.commands.run(
            f"tail -50 {PROCESS_COMPOSE_LOG} || true", user="root"
        ).stdout
        emit(self._event_sink, "browser.health_check.failed")
        raise RuntimeError(f"browsertool 未能在 60 秒内启动:\n{log}")


_global_manager: Optional[SandboxManager] = None


def get_global_manager() -> SandboxManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = SandboxManager()
    return _global_manager


def reset_global_manager() -> None:
    global _global_manager
    if _global_manager is not None:
        _global_manager.destroy()
    _global_manager = None
