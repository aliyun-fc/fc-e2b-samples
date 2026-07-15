# BrowserUse + E2B Browser Sandbox Demo

[中文文档](README_ZH-CN.md)

Run [BrowserUse](https://github.com/browser-use/browser-use) agents in an E2B
browser sandbox. The demo starts `browsertool` in the sandbox and connects
BrowserUse to its Chrome DevTools Protocol (CDP) endpoint with E2B's access
token. It includes a basic task and a multi-task session-reuse example.

## Run

```bash
cd e2b-browser-use
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

cp env.example .env
# Set E2B_API_KEY and the OpenAI-compatible provider variables in .env.

python examples/01_browseruse_basic.py
python examples/02_browseruse_advanced.py
```

No local browser service or second terminal is required.

## Verify the local lifecycle logic

The tests use fakes instead of a real E2B account, so they do not create a
sandbox or require API keys:

```bash
python -m unittest discover -s tests -v
```

They cover authenticated CDP endpoint construction, cleanup after setup
failures, session reuse, and safe replacement of an existing session.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `E2B_API_KEY` | yes | Creates and manages the E2B sandbox. |
| `E2B_API_URL` / `E2B_DOMAIN` | no | Optional E2B-compatible regional endpoint configuration. |
| `E2B_TEMPLATE` | no | Existing browser template to reuse. |
| `E2B_BROWSER_IMAGE` | no | Image used to build a temporary template when no template is set. |
| `E2B_TIMEOUT` | no | Sandbox lifetime in seconds; defaults to `600`. |
| `OPENAI_API_KEY` | yes | API key for an OpenAI-compatible chat-completions provider. |
| `OPENAI_BASE_URL` | no | Provider base URL; defaults to OpenAI. |
| `OPENAI_MODEL` | no | Model name; defaults to `gpt-4.1-mini`. |

## How it works

1. `SandboxManager` creates an E2B sandbox from `E2B_TEMPLATE`, or builds a
   temporary template from `E2B_BROWSER_IMAGE`.
2. It starts `browsertool` and waits for its health endpoint.
3. It gets the browsertool host from E2B and returns a CDP WebSocket URL plus
   the `X-Access-Token` header.
4. `Browser(..., cdp_url=..., headers=..., is_local=False)` attaches BrowserUse
   to that remote browser.
5. The examples stop BrowserUse and delete the E2B sandbox in `finally` blocks.

`examples/runner.py` caches active sandboxes by `(user_id, session_id,
thread_id)` within the Python process. Calling `create_or_get_sandbox` again
with the same values reuses the existing browser session.

## Troubleshooting

- **Missing environment variables**: copy `env.example` to `.env`, then set
  `E2B_API_KEY` and `OPENAI_API_KEY`.
- **browsertool does not become ready**: verify that the browser image is
  available to your E2B deployment. The raised error includes the browsertool
  process log tail.
- **CDP authentication error**: use a BrowserUse release that supports the
  remote-browser `headers` option (the requirement pins a compatible range).
