# LangChain + E2B PDF 转 Markdown

[English](README.md)

LangChain Agent 运行在控制端，E2B Sandbox 运行文档转换器。流程明确拆成三个独立步骤：

1. 构建并推送 Docker 镜像。
2. 根据镜像构建并持久化 E2B Template。
3. 使用已持久化的 Template ID 运行 LangChain Agent。

`main.py` 是 Agent 的 CLI 入口；`pdf_to_markdown_agent.py` 包含可复用的 E2B
转换 Tool 与 LangChain Agent 实现。PDF 转换过程中不会再构建 Template。

## 1. 构建并推送 Docker 镜像

`template/` 包含 Builder mode 源镜像及其文档转换依赖；LangChain 和 Agent 代码始终
运行在控制端。

```bash
export REGISTRY=fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"

docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" template/

export ACR_USERNAME=<仓库用户名>
export ACR_PASSWORD=<仓库密码或临时凭证>
printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
docker buildx imagetools inspect "$IMAGE"
```

## 2. 构建 E2B Template

配置控制端并安装依赖：

```bash
cp env.example .env
# 编辑 .env，填写 E2B_API_KEY、E2B_API_URL、E2B_DOMAIN 和 E2B_TEMPLATE_IMAGE。

uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```

`build_template.py` 调用 `Template().from_image(E2B_TEMPLATE_IMAGE)` 和
`Template.build(...)`，然后输出 `E2B_TEMPLATE_ID=<template-id>`。请将该值写入
`.env` 的 `E2B_TEMPLATE_ID`。只有镜像或 Template 配置变化时才需要重新构建。

若 E2B 控制面拉取私有镜像需要凭据，请在运行 `build_template.py` 前通过运行环境同时
设置 `E2B_TEMPLATE_SOURCE_USERNAME` 和 `E2B_TEMPLATE_SOURCE_PASSWORD`。

## 3. 运行 LangChain Agent

在 `.env` 中设置 `OPENAI_MODEL`、`OPENAI_API_KEY` 和 `OPENAI_BASE_URL`，然后运行：

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
