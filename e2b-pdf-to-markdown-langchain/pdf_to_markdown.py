"""Build an E2B template from the document image and convert one PDF."""

from __future__ import annotations

import argparse
import logging
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from e2b import Sandbox, Template

LOGGER = logging.getLogger("pdf_to_markdown")


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
CONVERTER_PATH = "/home/user/convert_pdf.py"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def build_document_template() -> str:
    """Build a Builder-mode E2B template from E2B_TEMPLATE_IMAGE."""
    image = _required_env("E2B_TEMPLATE_IMAGE")
    api_key = _required_env("E2B_API_KEY")
    LOGGER.info("[template] building from image=%s", image)
    headers = {}
    username = os.environ.get("E2B_TEMPLATE_SOURCE_USERNAME", "").strip()
    password = os.environ.get("E2B_TEMPLATE_SOURCE_PASSWORD", "").strip()
    if username or password:
        if not username or not password:
            raise RuntimeError("Set both E2B_TEMPLATE_SOURCE_USERNAME and E2B_TEMPLATE_SOURCE_PASSWORD")
        headers = {
            "X-E2B-Template-Source-Username": username,
            "X-E2B-Template-Source-Password": password,
        }
    name = f"document-conversion-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    build_kwargs = {
        "cpu_count": int(os.getenv("E2B_TEMPLATE_CPU", "2")),
        "memory_mb": int(os.getenv("E2B_TEMPLATE_MEMORY_MB", "2048")),
        "api_key": api_key,
        "api_url": os.getenv("E2B_API_URL") or None,
        "domain": os.getenv("E2B_DOMAIN") or None,
    }
    if headers:
        build_kwargs["headers"] = headers
    build = Template.build(
        Template().from_image(image),
        name=name,
        **build_kwargs,
    )
    template = getattr(build, "template_id", None) or build.name
    LOGGER.info("[template] ready template=%s", template)
    return template


def convert_pdf(pdf_path: str | Path) -> str:
    """Build a template, upload one PDF, and return converted Markdown."""
    load_dotenv(Path(__file__).with_name(".env"), override=True)
    source = Path(pdf_path).expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("pdf_path must point to an existing .pdf file")
    LOGGER.info("[input] PDF=%s (%d bytes)", source, source.stat().st_size)
    started_at = time.monotonic()
    template = build_document_template()
    LOGGER.info("[sandbox] creating from template=%s", template)
    sandbox = Sandbox.create(
        template=template,
        timeout=int(os.getenv("E2B_TIMEOUT", "600")),
        api_key=_required_env("E2B_API_KEY"),
        api_url=os.getenv("E2B_API_URL") or None,
        domain=os.getenv("E2B_DOMAIN") or None,
    )
    try:
        LOGGER.info("[sandbox] ready sandbox_id=%s", sandbox.sandbox_id)
        LOGGER.info("[upload] input.pdf")
        sandbox.files.write("/home/user/input.pdf", source.read_bytes())
        sandbox.files.write(CONVERTER_PATH, CONVERTER)
        LOGGER.info("[convert] running PyMuPDF")
        result = sandbox.commands.run(f"python {CONVERTER_PATH}", timeout=120)
        if result.exit_code != 0:
            raise RuntimeError(f"conversion failed: {result.stderr}")
        LOGGER.info("[convert] completed: %s", result.stdout.strip())
        markdown = sandbox.files.read("/home/user/output.md")
        LOGGER.info("[download] received %d characters in %.1fs", len(markdown), time.monotonic() - started_at)
        return markdown
    finally:
        LOGGER.info("[cleanup] killing sandbox_id=%s", sandbox.sandbox_id)
        sandbox.kill()
        LOGGER.info("[cleanup] sandbox removed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a PDF to Markdown through E2B")
    parser.add_argument("pdf", help="path to the local PDF")
    parser.add_argument("--output", type=Path, help="optional local Markdown destination")
    parser.add_argument("--direct", action="store_true", help="bypass the LangChain Tool")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for logger_name in ("e2b", "httpx", "httpcore"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    if args.direct:
        LOGGER.info("[workflow] direct E2B conversion")
        markdown = convert_pdf(args.pdf)
    else:
        LOGGER.info("[langchain] invoking convert_pdf_to_markdown Tool")
        from langchain_agent import convert_pdf_to_markdown
        markdown = convert_pdf_to_markdown.invoke({"pdf_path": args.pdf})
        LOGGER.info("[langchain] Tool invocation completed")
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
        LOGGER.info("[output] Markdown written to %s", args.output)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
