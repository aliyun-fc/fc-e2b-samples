"""Interactive LangChain + E2B browser sandbox demo with live event logs."""

import argparse
import signal
import sys
from typing import Any

from langchain_agent import create_browser_agent, get_sandbox_manager
from runtime_events import ConsoleEventLogger, redact_fields, redact_text


def cleanup_sandbox() -> None:
    manager = get_sandbox_manager()
    if manager.is_active():
        print(f"\n正在清理 sandbox…\n{manager.destroy()}")


def _response_content(result) -> str:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    return str(messages[-1].content) if messages else str(result)


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    return redact_text(content if isinstance(content, str) else str(content))


def _print_agent_update(update: dict[str, Any], verbose: bool) -> None:
    """Render LangChain's model/tool node updates without printing credentials."""
    for node, state in update.items():
        messages = state.get("messages", []) if isinstance(state, dict) else []
        if not messages:
            continue
        message = messages[-1]
        tool_calls = getattr(message, "tool_calls", []) or []
        if tool_calls:
            for call in tool_calls:
                name = call.get("name", "unknown")
                arguments = call.get("args", {})
                print(
                    f"[agent.tool_call] {name} | args={redact_fields(arguments)}",
                    flush=True,
                )
        elif node == "tools":
            print(f"[agent.tool_result] {_message_text(message)}", flush=True)
        elif verbose and _message_text(message):
            print(f"[agent.response] {_message_text(message)}", flush=True)


def run_query(agent: Any, query: str, verbose: bool) -> str:
    """Stream an agent run so model decisions and tool results are observable."""
    final_messages: list[Any] = []
    for update in agent.stream(
        {"messages": [{"role": "user", "content": query}]}, stream_mode="updates"
    ):
        if isinstance(update, dict):
            _print_agent_update(update, verbose)
            for state in update.values():
                if isinstance(state, dict) and state.get("messages"):
                    final_messages = state["messages"]
    return _response_content({"messages": final_messages})


def _check_local_dependencies() -> None:
    try:
        from playwright.sync_api import sync_playwright

        del sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "本地缺少 Playwright。请在本目录执行：\n"
            "  uv pip install -r requirements.txt\n"
            "Playwright 在本机用于连接 E2B 的远程浏览器，不安装在 sandbox 内。"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="LangChain + E2B browser sandbox demo")
    parser.add_argument("--quiet", action="store_true", help="隐藏实时运行日志，仅显示最终回答")
    args = parser.parse_args()
    def signal_handler(_signum, _frame):
        cleanup_sandbox()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    print("LangChain + E2B Browser Sandbox 示例")
    try:
        _check_local_dependencies()
        agent = create_browser_agent(event_sink=ConsoleEventLogger(enabled=not args.quiet))
        examples = [
            "创建一个浏览器 sandbox",
            "导航到 https://example.com 并告诉我页面标题",
            "截取当前页面截图",
        ]
        for query in examples:
            print(f"\n> {query}")
            print(run_query(agent, query, verbose=not args.quiet))

        print("\n进入交互模式（输入 quit 或 exit 退出）")
        while True:
            try:
                query = input("请输入您的查询: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if query.lower() in {"quit", "exit", "退出"}:
                break
            if query:
                print(run_query(agent, query, verbose=not args.quiet))
    finally:
        cleanup_sandbox()


if __name__ == "__main__":
    main()
