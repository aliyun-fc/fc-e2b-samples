# Browser Sandbox CDP Demo

Start browsertool inside a sandbox, expose the CDP (Chrome DevTools Protocol) WebSocket endpoint, and verify the connection with Playwright.

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
| `E2B_API_KEY` | yes | API Key |
| `E2B_API_URL` | yes | API URL, e.g. `https://api.us-west-1.e2b.fc.aliyuncs.com` |
| `E2B_DOMAIN` | yes | Domain, e.g. `us-west-1.e2b.fc.aliyuncs.com` |

## Workflow

1. Build a temporary template from the browser image
2. Create a sandbox instance
3. Start browsertool inside the sandbox (xvfb + vnc + chromium)
4. Wait for `/health` to return 200
5. Probe CDP WebSocket handshake (101 Switching Protocols)
6. Connect via Playwright over CDP, open example.com and verify
7. Destroy the sandbox
