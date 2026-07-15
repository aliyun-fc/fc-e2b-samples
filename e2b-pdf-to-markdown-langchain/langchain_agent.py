"""Expose PDF-to-Markdown conversion as a LangChain tool."""

from langchain.tools import tool
from langchain_openai import ChatOpenAI

from pdf_to_markdown import convert_pdf


@tool
def convert_pdf_to_markdown(pdf_path: str) -> str:
    """Convert a local PDF path to Markdown using the E2B document template."""
    return convert_pdf(pdf_path)


def create_agent():
    """Create a tool-calling agent; callers own invocation and model credentials."""
    from langchain.agents import create_agent

    model = ChatOpenAI()
    return create_agent(model, [convert_pdf_to_markdown])
