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

## 1. Build and push the Docker image

`template/` contains the Builder-mode source image and its dependencies.
LangChain and agent code remain on the controller.

```bash
export REGISTRY=fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"

docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" template/

export ACR_USERNAME=<registry-username>
export ACR_PASSWORD=<registry-password-or-temporary-token>
printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

## 2. Build the E2B template

Set up the controller configuration and dependencies:

```bash
cp env.example .env
# Edit .env: set E2B_API_KEY, E2B_API_URL, E2B_DOMAIN, and E2B_TEMPLATE_IMAGE.

uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```

`build_template.py` calls `Template().from_image(E2B_TEMPLATE_IMAGE)` and
`Template.build(...)`, then prints `E2B_TEMPLATE_ID=<template-id>`. Copy that
value into `.env` as `E2B_TEMPLATE_ID`. Rebuild only when the image or template
configuration changes.

If the E2B control plane needs private-image credentials, set both
`E2B_TEMPLATE_SOURCE_USERNAME` and `E2B_TEMPLATE_SOURCE_PASSWORD` in the
runtime environment before running `build_template.py`.

## 3. Run the LangChain agent

Set `OPENAI_MODEL`, `OPENAI_API_KEY`, and `OPENAI_BASE_URL` in `.env`, then:

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
