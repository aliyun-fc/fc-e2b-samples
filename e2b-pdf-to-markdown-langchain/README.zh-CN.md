# LangChain + E2B PDF 转 Markdown

[English](README.md)

本示例将 LangChain Agent 作为运行在控制端的编排程序，将 E2B Sandbox
作为文档转换工作节点。每次转换会根据镜像创建 E2B Template、创建 Sandbox、
上传 PDF、在 Sandbox 内转换、下载 Markdown，并在 `finally` 中销毁 Sandbox。

```text
LangChain / 控制端
        │ Template().from_image(镜像) + Template.build(...)
        ▼
E2B Sandbox（PyMuPDF、Poppler、Tesseract）
        │ 上传 PDF → 转换 → 下载 Markdown
        ▼
本地 Markdown 文件
```

## 构建文档转换镜像

本目录的 `Dockerfile` 是 E2B **Builder mode** 的源镜像，只安装 Sandbox
内部所需能力，不包含 LangChain 或 Agent 代码：

- Python：PyMuPDF（`fitz`）、`pdfplumber`、`pypdf`、`pytesseract`、Pillow
- 系统工具：`poppler-utils`、Tesseract OCR

设置镜像地址：

```bash
export REGISTRY=fc-e2b-dev-registry.cn-hangzhou.cr.aliyuncs.com
export IMAGE="$REGISTRY/custom/document-conversion-template:0.0.1"
```

按 E2B 镜像要求构建单一 AMD64 镜像，并关闭 provenance 与 SBOM attestations：

```bash
docker buildx build --load --platform linux/amd64 --provenance=false --sbom=false \
  -t "$IMAGE" .
```

## 登录并推送 ACR

```bash
export ACR_USERNAME=<仓库用户名>
export ACR_PASSWORD=<仓库密码或临时凭证>

printf '%s' "$ACR_PASSWORD" | docker login "$REGISTRY" \
  -u "$ACR_USERNAME" --password-stdin
docker push "$IMAGE"
```

推送后先验证远端 tag：

```bash
docker buildx imagetools inspect "$IMAGE"
```

## 通过 E2B 使用镜像

复制环境变量示例：

```bash
cp env.example .env
```

编辑 `.env`，至少填写：

```dotenv
E2B_API_KEY=<目标地域的 E2B API Key>
E2B_API_URL=https://api.us-west-1.e2b.fc.aliyuncs.com
E2B_DOMAIN=us-west-1.e2b.fc.aliyuncs.com
E2B_TEMPLATE_IMAGE=fc-e2b-dev-registry.cn-hangzhou.cr.aliyuncs.com/custom/document-conversion-template:0.0.1
```

如果 E2B 控制面可以直接拉取 ACR 镜像，请保持
`E2B_TEMPLATE_SOURCE_USERNAME` 与 `E2B_TEMPLATE_SOURCE_PASSWORD` 为空。
否则需填写这两个变量；示例会将其作为镜像拉取请求头传给 E2B，绝不会写入
代码或镜像。

运行转换控制端：

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python pdf_to_markdown.py ./demo.pdf --output demo.md
```

命令会输出 LangChain Tool 调用、Template 构建、Sandbox ID、上传、转换、下载和
清理日志。排查纯 E2B 路径时可加 `--direct`，跳过 LangChain Tool 包装层。

程序内部执行：

1. `Template().from_image(E2B_TEMPLATE_IMAGE)` 声明镜像来源；
2. `Template.build(...)` 以 Builder mode 构建临时 Template；
3. `Sandbox.create(...)` 创建文档转换环境；
4. 上传 PDF，在 Sandbox 内运行 PyMuPDF 转换脚本；
5. 下载 `/home/user/output.md`，并销毁 Sandbox。

`langchain_agent.py` 将转换流程导出为 `convert_pdf_to_markdown` Tool，可由
更大的 LangChain Agent 调用。

## 生产建议

- 使用不可变镜像 tag，便于追溯和回滚。
- 将 Template 构建与 PDF 转换分离，并持久化、复用已构建的 Template ID；本示例
  为了完整展示链路，每次转换都会构建临时 Template。
- 扫描版 PDF 需要在 Sandbox 转换脚本中增加 OCR 步骤；镜像已包含 Tesseract 与
  Poppler 基础工具。
- 将 ACR、E2B 与模型凭据放在环境变量或密钥管理服务中，禁止提交 `.env`。
