"""Run multiple BrowserUse tasks while reusing one E2B browser session."""

import asyncio

from common import create_logger, print_info, print_result, print_section, setup_example_environment, validate_settings

setup_example_environment()

from browser_use import Agent, Browser, ChatOpenAI
from config import get_settings
from runner import create_or_get_sandbox, destroy_sandbox


async def run_task(description: str, task: str, browser: Browser, llm: ChatOpenAI) -> dict[str, object]:
    print_section(description)
    result = await Agent(task=task, llm=llm, browser=browser).run()
    final_result = result.final_result()
    print_result(final_result)
    return {"task": description, "result": final_result, "steps": len(result.model_thoughts())}


async def main() -> None:
    settings = get_settings()
    print_section("BrowserUse + E2B: reusable multi-task session")
    if not validate_settings(settings):
        return
    sandbox = create_or_get_sandbox("advanced_user", "advanced_session", "multitask")
    logger = create_logger(sandbox["sandbox_id"])
    browser = None
    try:
        browser = Browser(cdp_url=sandbox["cdp_url"], headers=sandbox["cdp_headers"], is_local=False, keep_alive=True, user_agent=settings.user_agent)
        llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        tasks = [
            ("Task 1: inspect", "Visit https://example.com and report the page title."),
            ("Task 2: reuse", "On the current site, explain what the 'More information' link points to."),
            ("Task 3: verify", "State whether this is an example documentation page and why."),
        ]
        results = []
        for description, task in tasks:
            logger.info("Running %s", description)
            results.append(await run_task(description, task, browser, llm))
        print_section("Summary")
        print_info("Successful tasks", len(results))
        print_info("Total steps", sum(item["steps"] for item in results))
    finally:
        if browser:
            await browser.stop()
        destroy_sandbox(sandbox["sandbox_id"])


if __name__ == "__main__":
    asyncio.run(main())
