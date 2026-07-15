"""LangChain tools for operating an E2B browser sandbox."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from runtime_events import EventSink, emit
from sandbox_manager import SandboxManager


load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

_sandbox_manager: SandboxManager | None = None
_event_sink: EventSink | None = None
SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots"


def get_sandbox_manager() -> SandboxManager:
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(event_sink=_event_sink)
    return _sandbox_manager


def set_event_sink(event_sink: EventSink | None) -> None:
    """Configure runtime event output for tools and their sandbox manager."""
    global _event_sink
    _event_sink = event_sink
    if _sandbox_manager is not None:
        _sandbox_manager.set_event_sink(event_sink)


def _connect_browser(playwright):
    manager = get_sandbox_manager()
    return playwright.chromium.connect_over_cdp(
        manager.get_cdp_url(), headers=manager.get_cdp_headers()
    )


@tool
def create_browser_sandbox(idle_timeout: int | None = None) -> str:
    """创建或获取 E2B 浏览器 sandbox。需要浏览网页前先调用此工具。

    从 E2B_BROWSER_IMAGE 构建临时模板。
    """
    try:
        emit(_event_sink, "tool.started", tool="create_browser_sandbox", idle_timeout=idle_timeout)
        info = get_sandbox_manager().create(idle_timeout)
        result = (
            "Sandbox 创建成功。\n"
            f"- ID: {info['sandbox_id']}\n"
            f"- Template: {info['template']}"
        )
        emit(_event_sink, "tool.completed", tool="create_browser_sandbox", sandbox_id=info["sandbox_id"])
        return result
    except Exception as exc:
        emit(_event_sink, "tool.failed", tool="create_browser_sandbox", error=str(exc))
        return f"创建 Sandbox 失败: {exc}"


@tool
def get_sandbox_info() -> str:
    """获取当前 E2B sandbox 的 ID、CDP URL 和模板信息。"""
    try:
        emit(_event_sink, "tool.started", tool="get_sandbox_info")
        info = get_sandbox_manager().get_info()
        result = (
            "当前 Sandbox 信息：\n"
            f"- ID: {info['sandbox_id']}\n"
            f"- Template: {info['template']}"
        )
        emit(_event_sink, "tool.completed", tool="get_sandbox_info", sandbox_id=info["sandbox_id"])
        return result
    except Exception as exc:
        emit(_event_sink, "tool.failed", tool="get_sandbox_info", error=str(exc))
        return f"获取 Sandbox 信息失败: {exc}"


class NavigateInput(BaseModel):
    url: str = Field(description="要访问的 http:// 或 https:// URL")
    wait_until: str = Field(default="domcontentloaded", description="load、domcontentloaded 或 networkidle")
    timeout: int = Field(default=30000, description="超时时间（毫秒）")


@tool(args_schema=NavigateInput)
def navigate_to_url(url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> str:
    """通过已创建的 E2B browsertool CDP 连接导航到一个网页。"""
    if not url.startswith(("http://", "https://")):
        return f"无效 URL: {url}"
    manager = get_sandbox_manager()
    if not manager.is_active():
        return "请先创建 sandbox"
    try:
        emit(_event_sink, "tool.started", tool="navigate_to_url", url=url, wait_until=wait_until)
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = _connect_browser(playwright)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url, wait_until=wait_until, timeout=timeout)
                title = page.title()
                emit(_event_sink, "tool.completed", tool="navigate_to_url", url=url, title=title)
                return f"已导航到: {url}\n页面标题: {title}"
            finally:
                browser.close()
    except Exception as exc:
        emit(_event_sink, "tool.failed", tool="navigate_to_url", url=url, error=str(exc))
        return f"导航失败: {exc}"


@tool("browser_screenshot", description="保存当前 E2B 浏览器页面截图到本 demo 的 screenshots 目录。")
def take_screenshot(filename: str = "screenshot.png") -> str:
    """截取当前页面。filename 只能是文件名，防止写入 demo 目录外。"""
    manager = get_sandbox_manager()
    if not manager.is_active():
        return "请先创建 sandbox"
    output = SCREENSHOT_DIR / Path(filename).name
    if output.suffix.lower() != ".png":
        output = output.with_suffix(".png")
    try:
        emit(_event_sink, "tool.started", tool="browser_screenshot", filename=output.name)
        from playwright.sync_api import sync_playwright

        SCREENSHOT_DIR.mkdir(exist_ok=True)
        with sync_playwright() as playwright:
            browser = _connect_browser(playwright)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()
                page.screenshot(path=str(output), full_page=True)
            finally:
                browser.close()
        emit(_event_sink, "tool.completed", tool="browser_screenshot", path=str(output))
        return f"截图已保存: {output}"
    except Exception as exc:
        emit(_event_sink, "tool.failed", tool="browser_screenshot", error=str(exc))
        return f"截图失败: {exc}"


@tool("destroy_sandbox", description="销毁当前 E2B sandbox 并释放资源。仅在用户明确要求或程序结束时调用。")
def destroy_sandbox() -> str:
    """销毁当前 sandbox。"""
    emit(_event_sink, "tool.started", tool="destroy_sandbox")
    return get_sandbox_manager().destroy()


def create_browser_agent(system_prompt: str | None = None, event_sink: EventSink | None = None):
    """Create a LangChain agent backed by an OpenAI-compatible model."""
    set_event_sink(event_sink)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("请设置 OPENAI_API_KEY")
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=0.2,
    )
    prompt = system_prompt or """你是浏览器自动化助手。需要访问网页时，先创建 E2B sandbox，随后使用导航和截图工具。
一个 sandbox 可复用于多轮对话；仅在用户明确要求或对话结束时销毁它。工具失败时，明确报告失败原因，不得使用已有知识猜测页面内容或标题。请始终用中文回答。"""
    return create_agent(
        model=model,
        tools=[create_browser_sandbox, get_sandbox_info, navigate_to_url, take_screenshot, destroy_sandbox],
        system_prompt=prompt,
    )


def get_available_tools():
    return [create_browser_sandbox, get_sandbox_info, navigate_to_url, take_screenshot, destroy_sandbox]
