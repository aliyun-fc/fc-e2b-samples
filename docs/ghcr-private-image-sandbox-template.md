# Build a Sandbox Template from a Private GHCR Image

Cloud Sandbox can build a Sandbox template directly from a container registry image. Package a required language runtime, system dependencies, private SDKs, or data-science toolchain into an image, then build the template from that image. This is more controlled and reproducible than installing dependencies one-by-one at runtime.

This guide uses a private image in [GitHub Container Registry (GHCR)](https://ghcr.io) to build a template in the US West (Silicon Valley) region (`us-west-1`), create a Sandbox, and verify it. GHCR is authenticated, so the build request must include image-pull credentials.

## Use cases

- Package a shared Python or Node.js runtime and common dependencies for multiple agents.
- Install heavy data-science dependencies such as `pandas`, `numpy`, and plotting libraries once at build time.
- Use private SDKs or internal tools published only in a private GHCR repository.
- Version images and templates together for traceable builds and straightforward rollbacks.

## Prerequisites

- Cloud Sandbox is enabled and you have an `E2B_API_KEY` for the target region.
- The target is US West (Silicon Valley):
  - `api_url`: `https://api.us-west-1.e2b.fc.aliyuncs.com`
  - `domain`: `us-west-1.e2b.fc.aliyuncs.com`
- A GHCR image is available, for example `ghcr.io/<owner>/python:3.10`.
- GitHub credentials for pulling the image are ready (see [Registry credentials](#registry-credentials)).
- Install the `e2b` SDK:

```bash
pip install e2b
```

## Registry credentials

Pulling a private GHCR image requires a username and password. Use a GitHub [Personal Access Token (classic)](https://github.com/settings/tokens), not an account password:

- **Username**: the GitHub username that owns the image.
- **Password**: the Personal Access Token (classic), for example `ghp_xxxxxxxx`.

> **Required scopes**: enable `read:packages` and `write:packages` when creating the token. `read:packages` is required to pull the image during the build. A token with `write:packages` also includes `read:packages`. Missing scopes result in a 401 or 403 error while the build pulls the image; see the [GitHub Container Registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

Create the token in GitHub: **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**. Select `read:packages` and `write:packages` under **Select scopes**.

Pass the credentials as headers through the SDK's `headers` parameter:

| Header | Purpose | Value |
| --- | --- | --- |
| `X-E2B-Template-Source-Username` | Registry username | GitHub username |
| `X-E2B-Template-Source-Password` | Registry password | Personal Access Token (classic) |

> Credentials are sensitive. Inject them through environment variables or a secret manager; never hard-code them or commit them to the repository.

## Recommended workflow

Split the custom-image workflow into four steps:

1. Declare the image with `Template().from_image(<image>)` and provide registry credentials in `headers`.
2. Build the template with `Template.build`, specifying resources such as `cpu_count` and `memory_mb`, and save the resulting `template_id`.
3. Create a Sandbox with that `template_id`, wait for the data plane to become ready, and run a smoke test.
4. Destroy the Sandbox after verification to avoid holding resources.

Template building is a one-time operation. A `template_id` built from an image can be reused for many `Sandbox.create` calls. In production, build and execution are normally separate stages; do not rebuild the template before every run.

## Example

The following program builds a template from `ghcr.io/<owner>/python:3.10`, creates a Sandbox, verifies it by printing a marker, and then destroys it. The username, password, and `E2B_API_KEY` are read from environment variables.

```python
import os
import time
import uuid

from e2b import Sandbox, Template, default_build_logger

API_URL = "https://api.us-west-1.e2b.fc.aliyuncs.com"
DOMAIN = "us-west-1.e2b.fc.aliyuncs.com"
SOURCE_IMAGE = "ghcr.io/<owner>/python:3.10"
SANDBOX_MARKER = "sandbox-ok"
READY_TIMEOUT_SECONDS = 90
READY_INTERVAL_SECONDS = 3


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def main() -> int:
    # USERNAME is the GitHub username; PASSWORD is a classic PAT.
    username = required_env("USERNAME")
    password = required_env("PASSWORD")
    api_key = required_env("E2B_API_KEY")

    name = f"custom-python-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    headers = {
        "X-E2B-Template-Source-Username": username,
        "X-E2B-Template-Source-Password": password,
    }

    # 1. Build a template from the private GHCR image.
    build = Template.build(
        Template().from_image(SOURCE_IMAGE),
        name=name,
        cpu_count=2,
        memory_mb=2048,
        skip_cache=False,
        on_build_logs=default_build_logger(),
        headers=headers,
        api_key=api_key,
        api_url=API_URL,
        domain=DOMAIN,
    )
    print(f"template_id={build.template_id}")

    # 2. Create a Sandbox from the template.
    sandbox = Sandbox.create(
        template=build.template_id,
        timeout=900,
        api_key=api_key,
        api_url=API_URL,
        domain=DOMAIN,
    )
    print(f"sandbox_id={sandbox.sandbox_id}")

    try:
        # 3. Wait for readiness and run a smoke test.
        last_error = None
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            try:
                result = sandbox.commands.run(
                    f"python3 - <<'PY'\nprint('{SANDBOX_MARKER}')\nPY",
                    timeout=60,
                )
                break
            except Exception as err:
                last_error = err
                time.sleep(READY_INTERVAL_SECONDS)
        else:
            raise RuntimeError(f"Data plane did not become ready: {last_error}") from last_error

        if result.exit_code != 0 or SANDBOX_MARKER not in result.stdout:
            raise RuntimeError(
                f"Smoke test failed: exit={result.exit_code}, stdout={result.stdout}"
            )
        print(f"stdout={result.stdout.strip()}")
    finally:
        # 4. Always destroy the Sandbox.
        sandbox.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run it with credentials in environment variables:

```bash
export USERNAME="<github-username>"
export PASSWORD="ghp_xxxxxxxxxxxxxxxxxxxx"  # Personal Access Token (classic)
export E2B_API_KEY="<your-e2b-api-key>"
python3 build_from_ghcr.py
```

Successful output includes build logs, a `template_id`, a `sandbox_id`, and `sandbox-ok`. The program then destroys the Sandbox.

## Production guidance

- **Credential management**: inject the GitHub token and `E2B_API_KEY` through environment variables or a secret manager. Grant only the required package scopes and rotate tokens regularly.
- **Separate build from execution**: persist and reuse the `template_id`; do not rebuild before every Sandbox run.
- **Version images**: use explicit, immutable tags instead of relying only on `latest`, so templates can be traced and rolled back.
- **Size resources appropriately**: choose `cpu_count` and `memory_mb` for the image workload, increasing them for heavy dependencies or large-data processing.
- **Destroy Sandboxes promptly**: call `sandbox.kill()` in a `finally` block so failure paths do not leave resources running.

## Related capabilities

- [Run commands](../04.功能说明/03.Commands/02.运行命令.md)
- [Read and write files](../04.功能说明/04.Filesystem/02.读写文件.md)
- [Use Code Interpreter Sandbox](./01.使用%20Code%20Interpreter%20Sandbox.md)
