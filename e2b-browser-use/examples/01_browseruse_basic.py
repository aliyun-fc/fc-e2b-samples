"""Run one BrowserUse task in a browsertool-backed E2B sandbox."""

import asyncio

from common import create_logger, get_env_or_default, print_execution_stats, print_info, print_result, print_section, setup_example_environment, validate_settings

setup_example_environment()

from browser_use import Agent, Browser, ChatOpenAI
from config import get_settings
from runner import create_or_get_sandbox, destroy_sandbox


async def main() -> None:
    settings = get_settings()
    print_section("BrowserUse + E2B: basic task")
    if not validate_settings(settings):
        return
    sandbox = create_or_get_sandbox(
        user_id=get_env_or_default("USER_ID", "default_user"),
        session_id=get_env_or_default("SESSION_ID", "default_session"),
        thread_id=get_env_or_default("THREAD_ID", "default_thread"),
    )
    logger = create_logger(sandbox["sandbox_id"])
    browser = None
    try:
        print_info("Sandbox", sandbox["sandbox_id"])
        browser = Browser(
            cdp_url=sandbox["cdp_url"],
            headers=sandbox["cdp_headers"],
            is_local=False,
            keep_alive=True,
            user_agent=settings.user_agent,
        )
        llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        agent = Agent(
            task="Visit https://example.com, state its page title and summarize its purpose in one sentence.",
            llm=llm,
            browser=browser,
            use_vision=settings.browser_use_vision,
        )
        logger.info("Starting BrowserUse task")
        result = await agent.run()
        print_section("Task result")
        print_result(result.final_result())
        print_execution_stats(result)
    finally:
        if browser:
            await browser.stop()
        destroy_sandbox(sandbox["sandbox_id"])


if __name__ == "__main__":
    asyncio.run(main())
