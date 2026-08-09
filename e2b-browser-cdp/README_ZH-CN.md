# Browser Sandbox CDP 示例

[English](README.md)

面向阿里云 E2B 的 CDP demo。在 Sandbox 内启动 browsertool，暴露 CDP（Chrome
DevTools Protocol）WebSocket 端点，并使用 Playwright 验证连接。

本 demo 明确依赖阿里云 E2B endpoint 配置：`E2B_API_KEY`、`E2B_API_URL`、
`E2B_DOMAIN` 都是必填项。

## 运行

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium

cp env.example .env
# 编辑 .env，填写实际值。
python browser_sandbox_demo.py
```

## 环境变量

在 `.env` 中配置。文件通过 `load_dotenv(override=True)` 加载，因此会覆盖同名的 shell
环境变量。

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `E2B_API_KEY` | 是 | 阿里云 E2B API Key。 |
| `E2B_API_URL` | 是 | 阿里云 E2B API URL，例如 `https://api.us-west-1.e2b.fc.aliyuncs.com`。 |
| `E2B_DOMAIN` | 是 | 阿里云 E2B 域名，例如 `us-west-1.e2b.fc.aliyuncs.com`。 |

## Template 行为

本 demo 每次运行都会从写死的浏览器镜像构建临时 template：

```text
fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.44
```

这样可以让 demo 自包含，但有明确性能成本：启动更慢，重复运行会反复构建 template，
而不是复用预构建 template。生产环境或高频 demo 场景，应增加 template 复用能力，
传入预构建 template 名称。

## 工作流程

1. 根据写死的阿里云浏览器镜像构建临时 template。
2. 创建阿里云 E2B Sandbox 实例。
3. 在 Sandbox 内启动 browsertool（xvfb、vnc 和 chromium）。
4. 等待 `/health` 返回 200。
5. 探测 CDP WebSocket 握手（`101 Switching Protocols`）。
6. 通过 CDP 使用 Playwright 连接，打开 example.com 并验证结果。
7. 销毁 Sandbox。
