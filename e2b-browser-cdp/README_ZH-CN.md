# Browser Sandbox CDP 示例

[English](README.md)

在 Sandbox 内启动 browsertool，暴露 CDP（Chrome DevTools Protocol）WebSocket
端点，并使用 Playwright 验证连接。

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
| `E2B_API_KEY` | 是 | API Key。 |
| `E2B_API_URL` | 是 | API URL，例如 `https://api.us-west-1.e2b.fc.aliyuncs.com`。 |
| `E2B_DOMAIN` | 是 | 域名，例如 `us-west-1.e2b.fc.aliyuncs.com`。 |

## 工作流程

1. 根据浏览器镜像构建临时模板。
2. 创建 Sandbox 实例。
3. 在 Sandbox 内启动 browsertool（xvfb、vnc 和 chromium）。
4. 等待 `/health` 返回 200。
5. 探测 CDP WebSocket 握手（`101 Switching Protocols`）。
6. 通过 CDP 使用 Playwright 连接，打开 example.com 并验证结果。
7. 销毁 Sandbox。
