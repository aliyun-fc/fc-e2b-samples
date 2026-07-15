"""CLI entry point for the LangChain PDF-to-Markdown agent."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pdf_to_markdown_agent import load_environment, run_agent


LOGGER = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangChain PDF conversion agent")
    parser.add_argument("pdf", help="path to the local PDF")
    parser.add_argument("--output", type=Path, help="optional local Markdown destination")
    parser.add_argument("--direct", action="store_true", help="bypass the LangChain Tool")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_environment()
    markdown = run_agent(args.pdf, direct=args.direct)
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
        LOGGER.info("[output] Markdown written to %s", args.output)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
