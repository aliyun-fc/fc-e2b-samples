# LangChain + E2B PDF-to-Markdown

[中文文档](README_ZH-CN.md)

LangChain runs on the controller and E2B runs the document converter. The
workflow is intentionally split into three independent steps:

1. Build and push the Docker image.
2. Build and persist an E2B template from that image.
3. Run the LangChain agent using the persisted template ID.

`main.py` is the Agent CLI entry point. `pdf_to_markdown_agent.py` contains the
reusable E2B conversion Tool and LangChain Agent implementation; it never builds
a template during PDF conversion.

## Prerequisite: install uv

Install `uv` before building the E2B template. On macOS with Homebrew:

```bash
brew install uv
uv --version
```

On macOS or Linux without Homebrew, use the official installer, then start a new
shell (or reload its profile) before verifying the installation:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

See the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
for Windows and other installation methods.

## 1. Build and push the Docker image

`template/` contains the Builder-mode source image and its dependencies.
LangChain and agent code remain on the controller.

```bash
export REGISTRY=fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"

docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" template/

export ACR_USERNAME="<registry-username>"
export ACR_PASSWORD="<registry-password-or-temporary-token>"
printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

## Optional: publish to GHCR with GitHub Actions

The manual commands above remain the primary publishing path. As an optional
example, [`.github/workflows/publish-pdf-template-image.yml`](../.github/workflows/publish-pdf-template-image.yml)
publishes the same image to GHCR when manually started from the **Actions** tab,
or when a tag matching `e2b-pdf-to-markdown-langchain/v*` is pushed. It does
not run on branch pushes or pull requests.

Select **Publish PDF Template Image** → **Run workflow**, then enter an image
tag such as `0.0.1`. The workflow uses the repository `GITHUB_TOKEN` with
`packages: write` permission and publishes:

```text
ghcr.io/<repository-owner>/document-conversion-template:<image-tag>
```

For a tag-triggered publish, the `v` prefix is removed for the image tag. For
example, this publishes the image as `:0.0.1`:

```bash
git tag -a e2b-pdf-to-markdown-langchain/v0.0.1 -m "PDF template 0.0.1"
git push origin e2b-pdf-to-markdown-langchain/v0.0.1
```

After the first publish, set the package visibility and access policy in GitHub
Packages. A public GHCR package can be fetched by E2B without template-source
credentials. For a private package, put a GitHub username and a classic PAT with
`read:packages` in `E2B_TEMPLATE_SOURCE_USERNAME` and
`E2B_TEMPLATE_SOURCE_PASSWORD` in `.env`; do not commit that file. In either
case, set `E2B_TEMPLATE_IMAGE` to the complete `ghcr.io/...` image reference
before step 2.

## 2. Build the E2B template

Set up the controller configuration and dependencies:

```bash
cp env.example .env
# Edit .env as described below.

uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```

For this step, `E2B_API_KEY` and `E2B_TEMPLATE_IMAGE` are required. The image
must be the complete pushed image reference, matching `$IMAGE` from step 1.
`E2B_API_URL` and `E2B_DOMAIN` are optional in code; keep the example's
region-specific values when using that region, or leave both blank only when
the SDK default endpoint matches the API key.

`E2B_TEMPLATE_CPU` and `E2B_TEMPLATE_MEMORY_MB` control Template Build
resources and default to `2` CPU and `2048` MB when unset. If the E2B control
plane needs private-image credentials, set both
`E2B_TEMPLATE_SOURCE_USERNAME` and `E2B_TEMPLATE_SOURCE_PASSWORD` in `.env`.
The scripts load `.env` with override enabled, so shell exports of these values
are replaced by values in `.env`.

`build_template.py` calls `Template().from_image(E2B_TEMPLATE_IMAGE)` and
`Template.build(...)`, then prints `E2B_TEMPLATE_ID=<template-id>`. Copy that
value into `.env` as `E2B_TEMPLATE_ID`. Rebuild only when the image or template
configuration changes.

## 3. Run the LangChain agent

`E2B_API_KEY` and `E2B_TEMPLATE_ID` are required for every conversion.
`E2B_TIMEOUT` controls the sandbox lifetime and defaults to `600` seconds;
`E2B_API_URL` and `E2B_DOMAIN` use the same endpoint rules as step 2. For the
model-backed command, `OPENAI_API_KEY` is required, while `OPENAI_MODEL` and
`OPENAI_BASE_URL` default to `gpt-4o-mini` and `https://api.openai.com/v1`.
`--direct` does not require any `OPENAI_*` variable.

After setting the required values in `.env`, run:

```bash
python main.py ./report.pdf --output report.md
```

The agent must call `convert_pdf_to_markdown`. The Tool creates a sandbox from
`E2B_TEMPLATE_ID`, uploads the PDF, downloads the Markdown result, and always
destroys the sandbox. To diagnose the E2B conversion path without invoking a
model:

```bash
python main.py ./report.pdf --output report.md --direct
```

For scanned PDFs, add an OCR step to the sandbox conversion command.
