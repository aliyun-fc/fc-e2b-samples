# LangChain + E2B PDF-to-Markdown

[中文文档](README.zh-CN.md)

This demo keeps LangChain outside the sandbox and uses E2B only as a document
conversion worker. For every conversion it builds a Builder-mode template from
`E2B_TEMPLATE_IMAGE` with `Template().from_image(...)`, creates a sandbox,
uploads a PDF, executes the converter, downloads Markdown, and destroys the
sandbox.

## Build and publish the document-conversion image

This directory's `Dockerfile` is the Builder-mode source image for the template.
It installs `PyMuPDF` (`fitz`), `pdfplumber`, `pypdf`, `poppler-utils`, and
Tesseract. It deliberately does not copy LangChain or agent source code.

Set the image name once:

```bash
export REGISTRY=fc-e2b-dev-registry.cn-hangzhou.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"
```

Build one AMD64 image and disable provenance/SBOM attestations, as required for
E2B-compatible source images:

```bash
docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" .
```

Authenticate and push:

```bash
export ACR_USERNAME=<registry-username>
export ACR_PASSWORD=<registry-password-or-temporary-token>
printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
```

Confirm the remote image is present before using it:

```bash
docker buildx imagetools inspect "$IMAGE"
```

## Use the image through E2B

Copy the environment example and set the image name:

```bash
cp env.example .env
# Set E2B_API_KEY, E2B_API_URL, and E2B_DOMAIN for your E2B region.
# Edit .env and set E2B_TEMPLATE_IMAGE to the image that was just pushed.
```

When the E2B control plane can pull the ACR image without extra image-pull
credentials, leave `E2B_TEMPLATE_SOURCE_USERNAME` and
`E2B_TEMPLATE_SOURCE_PASSWORD` empty. The demo calls
`Template().from_image(E2B_TEMPLATE_IMAGE)` followed by `Template.build(...)`
in Builder mode, then creates a sandbox from the resulting template.

Install the controller dependencies and run a conversion:

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python pdf_to_markdown.py ./report.pdf --output report.md
```

The command logs LangChain Tool invocation, template build, sandbox ID, upload,
conversion, download, and cleanup. Use `--direct` only to diagnose the E2B path
without the LangChain Tool wrapper.

The command creates a temporary Template and sandbox, uploads the PDF, writes
Markdown locally, and destroys the sandbox in a `finally` block. For production,
persist and reuse the built template ID instead of building one per conversion.
For scanned PDFs, add an OCR step to the sandbox conversion command.

## Run

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
cp env.example .env
python pdf_to_markdown.py ./report.pdf --output report.md
```

`langchain_agent.py` exposes `convert_pdf_to_markdown` as a LangChain tool for
use in a larger agent workflow. It requires the OpenAI-compatible variables in
`.env` when the agent is created.
