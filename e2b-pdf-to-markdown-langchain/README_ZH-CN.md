# LangChain + E2B PDF 转 Markdown

[English](README.md)

LangChain Agent 运行在控制端，E2B Sandbox 运行文档转换器。流程明确拆成三个独立步骤：

1. 构建并推送 Docker 镜像。
2. 根据镜像构建并持久化 E2B Template。
3. 使用已持久化的 Template ID 运行 LangChain Agent。

`main.py` 是 Agent 的 CLI 入口；`pdf_to_markdown_agent.py` 包含可复用的 E2B
转换 Tool 与 LangChain Agent 实现。
Template 只需构建一次，重复使用，PDF 转换过程中不会再构建 Template。

## 0. 前置条件

### 0.1 安装 uv

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

### 0.2 获取 GitHub Personal Access Token (classic, PAT)

打开 [GitHub](https://github.com) 并登录，然后按以下步骤操作：

  1. 打开 GitHub → 头像 → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**。
  2. 选择 **Generate new token (classic)**。
  3. 填写名称与过期时间。
  4. 勾选 `write:packages`。E2B Template Build 会拉取源镜像并推送处理后的镜像，因此该权限必需。
  5. 点击生成并立即复制 token。
  6. 将 token 保存在安全的位置；GitHub 之后不会再次显示完整值。

## 1. 构建并推送镜像到 ghcr

`template/` 包含 Builder mode 源镜像及其文档转换依赖。以下命令在项目根目录执行。

### 1.1 构建镜像

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

## 2. 构建 E2B Template
### 2.1 环境变量配置

1. 必须设置 `E2B_API_KEY`。
2. 此阶段的 `E2B_TEMPLATE_IMAGE` 必须与第 1 步中的 `$IMAGE` 相同。
3. `E2B_API_URL` 和 `E2B_DOMAIN` 在代码中是可选项。使用下例中的地域时应保留对应值；只有 SDK 默认端点与 API Key 所属地域一致时才可同时留空。


创建 `.env`：

```bash
cp env.example .env
```

`.env` 示例：

```ini
E2B_API_KEY=e2b_your_api_key
# 默认使用 us-west-1 地域
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
# Sandbox 生命周期，单位为秒；未设置时默认 600。
E2B_TIMEOUT=600

# Template Build 配置；E2B_TEMPLATE_IMAGE 必填。
E2B_TEMPLATE_IMAGE=ghcr.io/aliyun-fc/document-conversion-template:0.0.2
# 私有 GHCR 镜像必须同时设置；使用带 write:packages 权限的 classic PAT。
E2B_TEMPLATE_SOURCE_USERNAME=your_github_username
E2B_TEMPLATE_SOURCE_PASSWORD=your_github_pat

# Template Build 资源；默认 CPU 2、内存 2048 MB。
E2B_TEMPLATE_CPU=2
E2B_TEMPLATE_MEMORY_MB=2048

# 运行 python build_template.py 后，将输出的值填写到这里。
E2B_TEMPLATE_ID=<template-id>
```

例外情况：

如果您使用阿里云容器镜像服务（ACR），且 ACR 账号与 E2B 的阿里云账号相同，则第 1 步应使用形如：
```
fc-e2b-dev-registry.us-west-1.cr.aliyuncs.com/custom/document-conversion-template:0.0.2
```
的镜像地址构建并推送；但在第 2 步中，您需要使用带 `-vpc` 后缀的地址：
```
fc-e2b-dev-registry-vpc.us-west-1.cr.aliyuncs.com/custom/document-conversion-template:0.0.2
```

说明：

- `E2B_TEMPLATE_CPU` 和 `E2B_TEMPLATE_MEMORY_MB` 控制 Template Build 资源；未设置时
默认分别为 `2` CPU 和 `2048` MB。
- GHCR package 必须保持私有，并在 `.env` 中同时设置
  `E2B_TEMPLATE_SOURCE_USERNAME` 和 `E2B_TEMPLATE_SOURCE_PASSWORD`；PAT 需要 `write:packages` 权限。
- 脚本以 override 模式加载 `.env`，因此 shell 中 export 的这两个值会被 `.env` 中的值覆盖。

### 2.2 初始化并构建模板

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python build_template.py
```


`build_template.py` 调用 `Template().from_image(E2B_TEMPLATE_IMAGE)` 和
`Template.build(...)`，然后输出 `E2B_TEMPLATE_ID=<template-id>`。请将该值写入
`.env` 的 `E2B_TEMPLATE_ID`。只有镜像或 Template 配置变化时才需要重新构建。

## 3. 运行 LangChain Agent

### 3.1 环境变量

1. `E2B_API_KEY` 必须正确配置。
2. `E2B_API_URL` 和 `E2B_DOMAIN` 需与第 2 步相同。
3. `E2B_TEMPLATE_ID` 需与第 2 步输出的值相同。
4. `E2B_TIMEOUT` 控制 Sandbox 生命周期，未设置时默认为 `600` 秒。
5. `OPENAI_API_KEY` 必填，`OPENAI_MODEL` 和
`OPENAI_BASE_URL` 默认分别为 `gpt-4o-mini` 与 `https://api.openai.com/v1`。

### 3.2 运行 Agent

在 `.env` 中填写所需变量后运行：

```bash
python main.py ./demo.pdf --output demo.md
```

该 demo 使用 `E2B_TEMPLATE_ID` 创建 Sandbox、上传 PDF、下载 Markdown，并始终销毁
Sandbox。若仅排查 E2B 转换路径而不调用模型，可使用 `--direct`：

```bash
python main.py ./demo.pdf --output demo.md --direct
```

## 4. 可选：使用 GitHub Actions 发布到 GHCR

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

首次发布后，请在 GitHub Packages 中将 package 保持为私有，并在 `.env` 中设置 GitHub 用户名
`E2B_TEMPLATE_SOURCE_USERNAME`，以及带 `write:packages` 权限的 classic PAT
`E2B_TEMPLATE_SOURCE_PASSWORD`；不要提交该文件。进入第 2 步前，应将 `E2B_TEMPLATE_IMAGE`
设置为完整的 `ghcr.io/...` 镜像地址。
