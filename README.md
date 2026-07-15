# E2B Sandbox Demos

This repository currently focuses on self-contained quick-start demos for
E2B-compatible sandboxes: code execution, browser automation, and agent tooling.

## Demo Index

| Demo | Directory | What It Shows | Runtime | Status |
| --- | --- | --- | --- | --- |
| Code Interpreter | `e2b-code-interpreter` | Create a Code Interpreter sandbox, run Python code, reuse state, and stop the sandbox | Python | available |
| Browser CDP | `e2b-browser-cdp` | Start browsertool in a sandbox, expose a CDP WebSocket endpoint, and verify it with Playwright | Python | available |
| BrowserUse Agent | `e2b-browser-use` | Run BrowserUse agents against browsertool in an E2B sandbox, including session reuse | Python | available |
| LangChain Browser Agent | `e2b-browser-langchain` | Use LangChain tools to create, navigate, screenshot, and clean up an E2B browser sandbox | Python | available |
| Browser Studio | `e2b-browser-studio` | Browser-focused API and frontend product shell | Python + TypeScript | scaffold |
| PDF-to-Markdown LangChain | `e2b-pdf-to-markdown-langchain` | LangChain Tool builds an E2B document template from an image, converts a PDF in a sandbox, and downloads Markdown | Python | available |
| Mastra Code Agent | `e2b-code-agent-mastra` | Use E2B from a Mastra agent through sandbox, code, file, command, and cleanup tools | TypeScript | available |

## Quick Start

Each demo is independent. Enter the directory, install dependencies, copy the
environment example, and run the command from that demo's README.

## Docker

Only the PDF-to-Markdown demo currently includes a Dockerfile. It is a
**Builder-mode source image** that installs document-conversion dependencies
inside the E2B sandbox (PyMuPDF, Poppler, and Tesseract); the LangChain agent
continues to run outside the sandbox. The demo calls `Template().from_image()`
and `Template.build()` to use this image end to end. See its
[English README](e2b-pdf-to-markdown-langchain/README.md) or
[中文 README](e2b-pdf-to-markdown-langchain/README.zh-CN.md) for build, ACR
push, and execution instructions.

Python demos:

```bash
cd e2b-code-interpreter
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
cp env.example .env
python code_exec.py
```

Browser-agent demos additionally need an OpenAI-compatible model configuration:

```bash
cd e2b-browser-use # or e2b-browser-langchain
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
cp env.example .env
python examples/01_browseruse_basic.py # BrowserUse
# or: python main.py                    # LangChain
```

Mastra demo:

```bash
cd e2b-code-agent-mastra
cp env.example .env
pnpm install
pnpm dev
```

## Environment Variables

| Variable | Used By | Description |
| --- | --- | --- |
| `E2B_API_KEY` | all demos | E2B API key |
| `E2B_API_URL` | all demos | Optional E2B-compatible control-plane API URL |
| `E2B_DOMAIN` | all demos | Optional E2B-compatible sandbox domain |
| `E2B_TEMPLATE` | BrowserUse, LangChain, Mastra | Template used when the agent creates a sandbox |
| `E2B_TEMPLATE_IMAGE` | PDF-to-Markdown LangChain | Published document-conversion source image used by `Template.from_image()` |
| `E2B_BROWSER_IMAGE` | BrowserUse, LangChain | Browser image used to build a temporary template when `E2B_TEMPLATE` is not set |
| `E2B_TIMEOUT` | BrowserUse, LangChain, Mastra | Sandbox lifetime timeout in seconds |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | BrowserUse, LangChain | OpenAI-compatible model configuration used by browser agents |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `MODEL` | Mastra | OpenAI-compatible model configuration used by the Mastra agent |

Do not commit real `.env` files or credentials.

## Repository Hygiene

- Keep each main demo runnable from its own directory.
- Keep generated files out of git: `.env`, `.venv`, `node_modules`, `dist`,
  logs, and caches.
- Keep historical or experimental demos under `_archive/`.
- Update this root README when adding or removing main demo directories.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
