"""
Start browsertool inside a sandbox, expose the CDP WebSocket endpoint,
and verify the connection with Playwright (open example.com and check title).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from e2b import Sandbox, Template

# Resolve .env relative to this script, not CWD.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

E2B_API_KEY = os.environ["E2B_API_KEY"]
E2B_API_URL = os.environ["E2B_API_URL"]
E2B_DOMAIN = os.environ["E2B_DOMAIN"]

IMAGE = "fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.44"
TEMPLATE_NAME = f"browser-sandbox-{int(time.time())}"

BROWSERTOOL_PORT = 3000
PC_CONFIG = "/etc/sandbox/config/process-compose.browsertool.yaml"
PC_LOG = "/tmp/browsertool-pc.log"


def start_browsertool(sbx: Sandbox) -> None:
    """Start xvfb / vnc / browsertool in the background and wait for port 3000."""
    # /tmp is a fresh tmpfs in the sandbox, so recreate the X11 socket dir as root.
    sbx.commands.run(
        "install -d -m 1777 /tmp/.X11-unix && "
        "rm -f /tmp/.X1-lock && "
        "mkdir -p /run/user/1000/dconf",
        user="root",
    )
    chrome_path = sbx.commands.run("cat /etc/browsertool/chrome-path", user="root").stdout.strip()

    # background=True is the real SDK background mode. `nohup ... &` makes the
    # SDK wait for command completion and appear to hang.
    proc = sbx.commands.run(
        f"process-compose up -f {PC_CONFIG} --tui=false --no-server > {PC_LOG} 2>&1",
        envs={"SXBT_BROWSER_CHROMIUM_PATH": chrome_path},
        background=True,
        user="root",
    )
    print(f"process-compose started (pid={proc.pid}), log: {PC_LOG}")

    deadline = time.time() + 60
    count = 0
    while time.time() < deadline:
        count += 1
        result = sbx.commands.run(
            f"curl -sS -m 2 -o /dev/null -w '%{{http_code}}' "
            f"http://localhost:{BROWSERTOOL_PORT}/health || true",
            user="root",
        )
        status = result.stdout.strip()
        print(f"  [check #{count}] /health -> {status}")
        if status == "200":
            return
        time.sleep(2)

    tail = sbx.commands.run(f"tail -50 {PC_LOG} || true", user="root").stdout
    raise RuntimeError(f"browsertool was not ready within 60s\n--- {PC_LOG} tail ---\n{tail}")


def verify_with_playwright(cdp_ws_url: str, headers: dict[str, str]) -> None:
    """Connect to browsertool over CDP, open example.com, and validate the title."""
    # Run the Playwright driver in a separate process session. In some local
    # terminal environments, driver teardown can signal its process group and
    # otherwise suppress the parent's final cleanup output.
    child_code = """
import os
from playwright.sync_api import sync_playwright

print("child: connecting", flush=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.connect_over_cdp(
        os.environ["CDP_URL"],
        headers={"X-Access-Token": os.environ["CDP_TOKEN"]},
        timeout=10_000,
    )
    print("child: connected", flush=True)
    try:
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        try:
            page.goto("https://example.com", wait_until="domcontentloaded", timeout=30_000)
            title = page.title()
            print(f"page.title() = {title!r}", flush=True)
            assert "Example" in title, f"unexpected title: {title!r}"
            print("Playwright over CDP verification passed", flush=True)
        finally:
            page.close()
    finally:
        browser.close()
"""
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", child_code],
        env={
            **os.environ,
            "CDP_URL": cdp_ws_url,
            "CDP_TOKEN": headers.get("X-Access-Token", ""),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        raise RuntimeError("Playwright CDP verification timed out after 90 seconds")
    if stdout:
        print("  " + stdout.replace("\n", "\n  ").rstrip())
    if process.returncode:
        raise RuntimeError(
            "Playwright CDP verification failed "
            f"(exit {process.returncode}):\n{stderr.strip()}"
        )


def verify_with_playwright_retry(cdp_ws_url: str, headers: dict[str, str]) -> None:
    """Retry Playwright CDP verification until browsertool is fully ready."""
    deadline = time.monotonic() + 90
    last_error = ""
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            print(f"Playwright CDP attempt #{attempt}")
            verify_with_playwright(cdp_ws_url, headers)
            return
        except RuntimeError as exc:
            last_error = str(exc)
            print(f"  not ready: {last_error.splitlines()[-1] if last_error else exc}")
            time.sleep(3)
    raise RuntimeError(f"Playwright CDP verification failed after retries:\n{last_error}")


def main() -> None:
    print(f"Building template from image: {IMAGE}")
    print(f"Template name: {TEMPLATE_NAME}")

    registry_template = Template().from_image(image=IMAGE)

    build_info = Template.build(
        registry_template,
        TEMPLATE_NAME,
        api_key=E2B_API_KEY,
        api_url=E2B_API_URL,
        domain=E2B_DOMAIN,
        cpu_count=2,
        memory_mb=2048,
    )
    template = build_info.name
    print(f"Template built: {template}")

    print("Creating sandbox")
    sbx = Sandbox.create(
        template=template,
        api_key=E2B_API_KEY,
        api_url=E2B_API_URL,
        domain=E2B_DOMAIN,
        timeout=600,
        allow_internet_access=True,
    )
    print(f"Sandbox created: {sbx.sandbox_id}")

    try:
        print(f"\n--- Starting browsertool on port {BROWSERTOOL_PORT} ---")
        start_browsertool(sbx)
        print("browsertool /health is ready")

        print("\n--- Internal CDP WebSocket handshake probe ---")
        probe = sbx.commands.run(
            f"curl -sS -m 4 -i "
            f"-H 'Connection: Upgrade' -H 'Upgrade: websocket' "
            f"-H 'Sec-WebSocket-Version: 13' "
            f"-H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' "
            f"http://localhost:{BROWSERTOOL_PORT}/ws/automation || true",
            user="root",
        )
        first_line = probe.stdout.splitlines()[0] if probe.stdout else ""
        print(f"Internal handshake response: {first_line}")
        if "101" not in first_line:
            print(f"[!] Did not get 101 Switching Protocols, output:\n{probe.stdout[:500]}")

        host = sbx.get_host(BROWSERTOOL_PORT)
        cdp_ws_url = f"wss://{host}/ws/automation"
        print("\n--- CDP WebSocket endpoint ---")
        print(f"  host: {host}")
        print(f"  CDP : {cdp_ws_url}")

        print("\n--- Playwright CDP case ---")
        headers = {}
        token = sbx._envd_access_token
        if token:
            headers["X-Access-Token"] = token
        verify_with_playwright_retry(cdp_ws_url, headers)
    finally:
        sbx.kill()
        print("\nSandbox killed")


if __name__ == "__main__":
    main()
