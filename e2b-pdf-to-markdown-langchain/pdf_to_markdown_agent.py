"""E2B PDF conversion Tool and LangChain agent runtime."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from e2b import Sandbox
from langchain.tools import tool
from langchain_openai import ChatOpenAI


LOGGER = logging.getLogger("pdf_to_markdown_agent")
LLM_LOG_PREVIEW_LIMIT = 1_000
CONVERTER_PATH = "/home/user/convert_pdf.py"
CONVERTER = r'''
import fitz
from pathlib import Path

source = Path("/home/user/input.pdf")
target = Path("/home/user/output.md")
document = fitz.open(source)
parts = []
for page_number, page in enumerate(document, start=1):
    text = page.get_text("text").strip()
    parts.append(f"## Page {page_number}\n\n{text}" if text else f"## Page {page_number}\n\n[No extractable text]")
target.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
print(f"converted {len(document)} pages")
'''
SYSTEM_PROMPT = """You are a document-conversion agent.
When the user asks to convert a PDF, you must call convert_pdf_to_markdown with
the exact local PDF path. Do not claim a conversion succeeded without calling
the tool. The tool result is the authoritative Markdown output."""


def required_env(name: str) -> str:
    """Return a required environment variable without exposing its value."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def load_environment() -> None:
    """Load the project-root .env file before reading runtime settings."""
    load_dotenv(Path(__file__).with_name(".env"), override=True)


def _template_id(template_id: str | None) -> str:
    return template_id.strip() if template_id and template_id.strip() else required_env("E2B_TEMPLATE_ID")


def convert_pdf(pdf_path: str | Path, template_id: str | None = None) -> str:
    """Convert one PDF using an already-built E2B template."""
    load_environment()
    source = Path(pdf_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("pdf_path must point to an existing .pdf file")
    LOGGER.info("[input] PDF=%s (%d bytes)", source, source.stat().st_size)
    started_at = time.monotonic()
    sandbox = Sandbox.create(
        template=_template_id(template_id),
        timeout=int(os.getenv("E2B_TIMEOUT", "600")),
        api_key=required_env("E2B_API_KEY"),
        api_url=required_env("E2B_API_URL"),
        domain=required_env("E2B_DOMAIN"),
    )
    try:
        LOGGER.info("[sandbox] ready sandbox_id=%s", sandbox.sandbox_id)
        sandbox.files.write("/home/user/input.pdf", source.read_bytes())
        sandbox.files.write(CONVERTER_PATH, CONVERTER)
        result = sandbox.commands.run(f"python {CONVERTER_PATH}", timeout=120)
        if result.exit_code != 0:
            raise RuntimeError(f"conversion failed: {result.stderr}")
        markdown = sandbox.files.read("/home/user/output.md")
        LOGGER.info("[download] received %d characters in %.1fs", len(markdown), time.monotonic() - started_at)
        return markdown
    finally:
        LOGGER.info("[cleanup] killing sandbox_id=%s", sandbox.sandbox_id)
        sandbox.kill()


@tool(return_direct=True)
def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert a local PDF path to Markdown using the E2B document template."""
    return convert_pdf(pdf_path)


def create_agent(model_name: str, openai_api_key: str, openai_base_url: str):
    """Create a LangChain agent with the PDF conversion Tool."""
    from langchain.agents import create_agent as create_langchain_agent

    model = ChatOpenAI(model=model_name, api_key=openai_api_key, base_url=openai_base_url)
    return create_langchain_agent(model, [convert_pdf_to_markdown], system_prompt=SYSTEM_PROMPT)


def run_agent(pdf_path: str | Path, *, direct: bool = False) -> str:
    """Run direct conversion or the LangChain PDF conversion agent."""
    if direct:
        return convert_pdf(pdf_path)
    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    api_key = required_env("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    LOGGER.info("[llm] model=%s base_url=%s", model_name, base_url)
    agent = create_agent(model_name, api_key, base_url)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Convert this PDF to Markdown: {pdf_path}"}]}
    )
    tool_messages = [
        message for message in result.get("messages", []) if message.__class__.__name__ == "ToolMessage"
    ]
    if not tool_messages:
        raise RuntimeError("LangChain agent completed without calling the PDF conversion tool")
    return str(tool_messages[-1].content)
