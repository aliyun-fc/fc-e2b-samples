# Browser Sandbox CDP Demo

[中文文档](README_ZH-CN.md)

Alibaba Cloud E2B demo. Start browsertool inside a sandbox, expose the CDP
(Chrome DevTools Protocol) WebSocket endpoint, and verify the connection with
Playwright.

This demo intentionally uses Alibaba Cloud E2B endpoint settings:
`E2B_API_KEY`, `E2B_API_URL`, and `E2B_DOMAIN` are required.

## Run

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium

cp env.example .env
# Edit .env with actual values
python browser_sandbox_demo.py
```

## Environment Variables

Configure in `.env` (loaded via `load_dotenv(override=True)`, which overrides shell env vars of the same name):

| Variable | Required | Description |
| --- | --- | --- |
| `E2B_API_KEY` | yes | Alibaba Cloud E2B API Key |
| `E2B_API_URL` | yes | Alibaba Cloud E2B API URL, e.g. `https://api.us-west-1.e2b.fc.aliyuncs.com` |
| `E2B_DOMAIN` | yes | Alibaba Cloud E2B domain, e.g. `us-west-1.e2b.fc.aliyuncs.com` |

## Template behavior

The demo builds a temporary template on every run from a hard-coded browser
image:

```text
fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.44
```

This keeps the demo self-contained, but it has a clear performance cost:
startup is slower and repeated runs rebuild templates instead of reusing a
prebuilt one. For production or repeated demos, add template reuse support and
pass a prebuilt template name instead.

## Workflow

1. Build a temporary template from the hard-coded Alibaba Cloud browser image
2. Create an Alibaba Cloud E2B sandbox instance
3. Start browsertool inside the sandbox (xvfb + vnc + chromium)
4. Wait for `/health` to return 200
5. Probe CDP WebSocket handshake (101 Switching Protocols)
6. Connect via Playwright over CDP, open example.com and verify
7. Destroy the sandbox
