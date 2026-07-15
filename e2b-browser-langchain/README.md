# LangChain + E2B Browser Sandbox

[中文文档](README_ZH-CN.md)

An interactive browser-automation demo using a LangChain agent and an Alibaba Cloud E2B
Browser Sandbox. The agent connects to Chromium through browsertool's CDP
WebSocket endpoint to navigate pages and take screenshots. The CDP connection
automatically includes the E2B access token.

## Features

- Create, inspect, and destroy E2B browser sandboxes.
- Build a temporary browser template from `E2B_BROWSER_IMAGE`.
- Start browsertool in the sandbox and wait for its health check.
- Navigate pages through an authenticated CDP connection with Playwright.
- Save screenshots locally in `screenshots/`.
- Use any OpenAI-compatible Chat Completions API with the LangChain agent.
- Run a preset demo or interactive session, with cleanup on exit.

## Install and run

Python 3.10 or later is required.

```bash
cd <demo-directory>
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium

cp env.example .env
# Edit .env and set E2B_API_KEY, E2B_API_URL, E2B_DOMAIN, and model settings.
python main.py
```

The default command emits phase logs for agent tool calls, template builds,
sandbox creation, browser health checks, and Playwright tools. CDP URLs and
authentication tokens are redacted. To print only the final answer:

```bash
python main.py --quiet
```

The program creates an agent, creates a sandbox, opens `https://example.com`,
saves a screenshot, and then enters interactive mode. Enter `quit` or `exit`,
or press Ctrl+C/Ctrl+D, to destroy the sandbox.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `E2B_API_KEY` | yes | Alibaba Cloud E2B API key. |
| `E2B_API_URL` | yes | Alibaba Cloud E2B API URL. |
| `E2B_DOMAIN` | yes | Alibaba Cloud E2B sandbox domain. |
| `E2B_BROWSER_IMAGE` | no | Image used to build the temporary browser template; the built-in image is used by default. |
| `E2B_TIMEOUT` | no | Sandbox lifetime in seconds; defaults to `600`. |
| `OPENAI_API_KEY` | yes | API key for the OpenAI-compatible provider. |
| `OPENAI_BASE_URL` | no | OpenAI-compatible API base URL; defaults to `https://api.openai.com/v1`. |
| `OPENAI_MODEL` | no | Model name; defaults to `gpt-4o-mini`. |

## Tools

| Tool | Purpose |
| --- | --- |
| `create_browser_sandbox` | Create or reuse an E2B sandbox and start browsertool. |
| `get_sandbox_info` | Return the sandbox ID, CDP address, and template name. |
| `navigate_to_url` | Visit a page through the CDP connection with authentication headers. |
| `browser_screenshot` | Save the current-page PNG screenshot to `screenshots/`. |
| `destroy_sandbox` | Destroy the sandbox and release resources. |

## Project structure

```text
e2b-browser-langchain/
├── main.py              # Demo and interactive entry point
├── langchain_agent.py   # Agent and browser tools
├── sandbox_manager.py   # E2B template, sandbox, browsertool, and CDP lifecycle
├── env.example          # Configuration example
└── requirements.txt     # Python dependencies
```

## How it works

1. `SandboxManager` builds a temporary template from `E2B_BROWSER_IMAGE` and creates a sandbox from it.
2. The manager starts browsertool in the sandbox and polls `http://localhost:3000/health`.
3. `sandbox.get_host(3000)` supplies the public host used to form the `/ws/automation` CDP WebSocket URL.
4. Playwright calls `connect_over_cdp` with the `X-Access-Token` header.
5. The program calls `sandbox.kill()` on exit.

The browser screenshot is the observable output of this demo and does not need
an additional remote-desktop service.
