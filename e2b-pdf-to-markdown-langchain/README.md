# LangChain + E2B PDF-to-Markdown

[中文文档](README_ZH-CN.md)

The LangChain Agent runs on the controller and the E2B Sandbox runs the
document converter. The workflow is split into three independent steps:

1. Build and push the Docker image.
2. Build and persist an E2B template from that image.
3. Run the LangChain Agent using the persisted template ID.

`main.py` is the Agent CLI entry point. `pdf_to_markdown_agent.py` contains the
reusable E2B conversion Tool and LangChain Agent implementation. Build the
template once and reuse it; PDF conversion never builds a template.

## 0. Prerequisites

### 0.1 Install uv

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

### 0.2 Create a GitHub Personal Access Token (classic, PAT)

Sign in to [GitHub](https://github.com), then:

  1. Open GitHub → profile picture → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
  2. Select **Generate new token (classic)**.
  3. Enter a name and expiration date.
  4. Select `write:packages`. Template Build pulls the source image and pushes the processed image, so this permission is required.
  5. Generate and copy the token immediately.
  6. Store the token securely; GitHub does not display the complete token again.

## 1. Build and push the image to GHCR

`template/` contains the Builder-mode source image and its document-conversion
dependencies. Run the following commands from this project directory.

### 1.1 Build the image

```bash
export IMAGE="ghcr.io/<github-username>/document-conversion-template:0.0.2"
export GHCR_USERNAME="<github-username>"
export GHCR_TOKEN="<classic-pat-with-write-packages>"

docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" template/

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

## 2. Build the E2B template

### 2.1 Configure environment variables

1. `E2B_API_KEY` is required.
2. `E2B_TEMPLATE_IMAGE` must match `$IMAGE` from step 1.
3. `E2B_API_URL` and `E2B_DOMAIN` are optional in code. Keep the matching regional values when using the region shown below; leave both blank only when the SDK default endpoint matches the API key's region.

Create `.env`:

```bash
cp env.example .env
```

Example `.env`:

```ini
E2B_API_KEY=e2b_your_api_key
# Use the us-west-1 region by default.
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
# Sandbox lifetime in seconds. Defaults to 600 when unset.
E2B_TIMEOUT=600

# Template Build configuration. E2B_TEMPLATE_IMAGE is required.
E2B_TEMPLATE_IMAGE=ghcr.io/aliyun-fc/document-conversion-template:0.0.2
# A private GHCR image requires both values and a classic PAT with write:packages.
E2B_TEMPLATE_SOURCE_USERNAME=your_github_username
E2B_TEMPLATE_SOURCE_PASSWORD=your_github_pat

# Template Build resources. Defaults: CPU 2 and memory 2048 MB.
E2B_TEMPLATE_CPU=2
E2B_TEMPLATE_MEMORY_MB=2048

# Set this to the value printed by python build_template.py.
E2B_TEMPLATE_ID=<template-id>
```

Exception:

When using Alibaba Cloud Container Registry (ACR), and the ACR account is the
same Alibaba Cloud account as E2B, use an image address such as the following in
step 1:

```text
fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com/custom/document-conversion-template:0.0.2
```

Build and push that image, but use the address with the `-vpc` suffix in step 2:

```text
fc-e2b-dev-registry-vpc.us-west-1.cr.aliyuncs.com/custom/document-conversion-template:0.0.2
```

Notes:

- `E2B_TEMPLATE_CPU` and `E2B_TEMPLATE_MEMORY_MB` control Template Build resources and default to `2` CPU and `2048` MB when unset.
- Keep the GHCR package private and set both `E2B_TEMPLATE_SOURCE_USERNAME` and `E2B_TEMPLATE_SOURCE_PASSWORD` in `.env`; the PAT needs `write:packages` permission.
- The scripts load `.env` with override enabled, so values in `.env` replace shell exports of these variables.

### 2.2 Initialize and build the template

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```

`build_template.py` calls `Template().from_image(E2B_TEMPLATE_IMAGE)` and
`Template.build(...)`, then prints `E2B_TEMPLATE_ID=<template-id>`. Copy that
value into `.env` as `E2B_TEMPLATE_ID`. Rebuild only when the image or template
configuration changes.

## 3. Run the LangChain Agent

### 3.1 Environment variables

1. `E2B_API_KEY` must be configured correctly.
2. `E2B_API_URL` and `E2B_DOMAIN` must match the values from step 2.
3. `E2B_TEMPLATE_ID` must match the value printed in step 2.
4. `E2B_TIMEOUT` controls the Sandbox lifetime and defaults to `600` seconds when unset.
5. `OPENAI_API_KEY` is required. `OPENAI_MODEL` and `OPENAI_BASE_URL` default to `gpt-4o-mini` and `https://api.openai.com/v1`.

### 3.2 Run the Agent

After setting the required values in `.env`, run:

```bash
python main.py ./demo.pdf --output demo.md
```

The demo creates a Sandbox from `E2B_TEMPLATE_ID`, uploads the PDF, downloads
the Markdown, and always destroys the Sandbox. To diagnose only the E2B
conversion path without calling a model, use `--direct`:

```bash
python main.py ./demo.pdf --output demo.md --direct
```

## 4. Optional: publish to GHCR with GitHub Actions

The local manual commands above remain the primary publishing path. As an
optional example, [`.github/workflows/publish-pdf-template-image.yml`](../.github/workflows/publish-pdf-template-image.yml)
can be started manually from the **Actions** tab. It also publishes the same
image to GHCR when a tag matching `e2b-pdf-to-markdown-langchain/v*` is pushed;
it does not run on branch pushes or pull requests.

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

After the first publish, keep the package private in GitHub Packages. Set a
GitHub username in `E2B_TEMPLATE_SOURCE_USERNAME` and a classic PAT with
`write:packages` in `E2B_TEMPLATE_SOURCE_PASSWORD` in `.env`; do not commit
that file. Before step 2, set `E2B_TEMPLATE_IMAGE` to the complete
`ghcr.io/...` image reference.
