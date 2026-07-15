# LangChain + E2B PDF 转 Markdown

[English](README.md)

LangChain Agent 运行在控制端，E2B Sandbox 运行文档转换器。流程明确拆成三个独立步骤：

1. 构建并推送 Docker 镜像。
2. 根据镜像构建并持久化 E2B Template。
3. 使用已持久化的 Template ID 运行 LangChain Agent。

`main.py` 是 Agent 的 CLI 入口；`pdf_to_markdown_agent.py` 包含可复用的 E2B
转换 Tool 与 LangChain Agent 实现。PDF 转换过程中不会再构建 Template。

## 前置条件：安装 uv

构建 E2B Template 前需要安装 `uv`。macOS 且已安装 Homebrew 时可运行：

```bash
brew install uv
uv --version
```

macOS 或 Linux 未使用 Homebrew 时，可使用官方安装器；完成后请重新打开终端（或重新加载
shell 配置）再验证安装：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

Windows 及其他安装方式请参阅 [uv 官方安装指南](https://docs.astral.sh/uv/getting-started/installation/)。

## 1. 构建并推送 Docker 镜像

`template/` 包含 Builder mode 源镜像及其文档转换依赖；LangChain 和 Agent 代码始终
运行在控制端。

```bash
export REGISTRY=fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"

docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" template/

export ACR_USERNAME="<仓库用户名>"
export ACR_PASSWORD="<仓库密码或临时凭证>"
printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

## 可选：通过 GitHub Actions 发布到 GHCR

上文的本地手动命令仍是主要发布方式。作为可选示例，
[`.github/workflows/publish-pdf-template-image.yml`](../.github/workflows/publish-pdf-template-image.yml)
可在 **Actions** 页面手动触发，也会在推送匹配
`e2b-pdf-to-markdown-langchain/v*` 的 tag 时将相同镜像发布至 GHCR；不会在分支 push 或
Pull Request 时运行。

选择 **Publish PDF Template Image** → **Run workflow**，输入如 `0.0.1` 的镜像标签。该
工作流使用仓库的 `GITHUB_TOKEN` 和 `packages: write` 权限，发布镜像地址为：

```text
ghcr.io/<repository-owner>/document-conversion-template:<image-tag>
```

通过 tag 触发时，镜像标签会移除 `v` 前缀。例如，以下命令会发布标签为 `:0.0.1` 的镜像：

```bash
git tag -a e2b-pdf-to-markdown-langchain/v0.0.1 -m "PDF template 0.0.1"
git push origin e2b-pdf-to-markdown-langchain/v0.0.1
```

首次发布后，请在 GitHub Packages 中设置 package 的可见性和访问策略。公开的 GHCR package
可由 E2B 直接拉取，无需 Template source 凭据。若 package 为私有，请在 `.env` 中设置 GitHub
用户名 `E2B_TEMPLATE_SOURCE_USERNAME`，以及带 `read:packages` 权限的 classic PAT
`E2B_TEMPLATE_SOURCE_PASSWORD`；不要提交该文件。无论 package 是否公开，进入第 2 步前都应将
`E2B_TEMPLATE_IMAGE` 设置为完整的 `ghcr.io/...` 镜像地址。

## 2. 构建 E2B Template

配置控制端并安装依赖：

```bash
cp env.example .env
# 按下文说明编辑 .env。

uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```

此阶段必须设置 `E2B_API_KEY` 和 `E2B_TEMPLATE_IMAGE`。镜像必须是完整的已推送镜像
地址，并且应与第 1 步的 `$IMAGE` 相同。代码将 `E2B_API_URL` 和 `E2B_DOMAIN` 视为
可选项：使用示例地域时保留示例中的区域值；只有 SDK 默认端点与 API Key 所属地域一致时
才可同时留空。

`E2B_TEMPLATE_CPU` 和 `E2B_TEMPLATE_MEMORY_MB` 控制 Template Build 资源；未设置时
默认分别为 `2` CPU 和 `2048` MB。若 E2B 控制面拉取私有镜像需要凭据，必须在 `.env`
中同时设置 `E2B_TEMPLATE_SOURCE_USERNAME` 和 `E2B_TEMPLATE_SOURCE_PASSWORD`。脚本以
override 模式加载 `.env`，因此 shell 中 export 的这两个值会被 `.env` 中的值覆盖。

`build_template.py` 调用 `Template().from_image(E2B_TEMPLATE_IMAGE)` 和
`Template.build(...)`，然后输出 `E2B_TEMPLATE_ID=<template-id>`。请将该值写入
`.env` 的 `E2B_TEMPLATE_ID`。只有镜像或 Template 配置变化时才需要重新构建。

## 3. 运行 LangChain Agent

每次转换都必须设置 `E2B_API_KEY` 和 `E2B_TEMPLATE_ID`。`E2B_TIMEOUT` 控制 Sandbox
生命周期，未设置时默认为 `600` 秒；`E2B_API_URL` 和 `E2B_DOMAIN` 遵循第 2 步相同的
端点规则。运行模型驱动的命令时 `OPENAI_API_KEY` 必填，`OPENAI_MODEL` 和
`OPENAI_BASE_URL` 默认分别为 `gpt-4o-mini` 与 `https://api.openai.com/v1`。`--direct`
不需要任何 `OPENAI_*` 变量。

在 `.env` 中填写所需变量后运行：

```bash
python main.py ./demo.pdf --output demo.md
```

Agent 必须调用 `convert_pdf_to_markdown`。该 Tool 使用 `E2B_TEMPLATE_ID` 创建
Sandbox、上传 PDF、下载 Markdown，并始终销毁 Sandbox。若仅排查 E2B 转换路径、
不调用模型：

```bash
python main.py ./demo.pdf --output demo.md --direct
```

扫描版 PDF 需要在 Sandbox 转换命令中增加 OCR 步骤。
