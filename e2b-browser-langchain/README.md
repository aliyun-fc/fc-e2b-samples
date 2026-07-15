# LangChain + E2B Browser Sandbox

一个使用 LangChain Agent 和 E2B Browser Sandbox 的交互式浏览器自动化示例。Agent 通过 browsertool 的 CDP WebSocket 连接 Chromium，执行导航和截图；CDP 连接会自动携带 E2B 访问令牌。

## 功能

- 创建、查询和销毁 E2B browser sandbox
- 从 `E2B_BROWSER_IMAGE` 构建临时浏览器模板
- 在 sandbox 内启动 browsertool 并等待健康检查
- 用 Playwright 通过已认证 CDP 连接导航网页
- 保存截图至本地 `screenshots/`
- 使用任意 OpenAI-compatible Chat Completions API 驱动 LangChain Agent
- 支持预设演示与交互模式，退出时自动清理 sandbox

## 安装与运行

需要 Python 3.10+。

```bash
cd <demo-directory>
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium

cp env.example .env
# 编辑 .env，填写 E2B_API_KEY 和 OpenAI-compatible 模型配置
python main.py
```

默认会实时输出 `agent.tool_call`、`agent.tool_result`、模板构建、sandbox 创建、browser health check 与 Playwright 工具的阶段日志。日志会隐藏 CDP URL 和认证 token。若只需要最终回答：

```bash
python main.py --quiet
```

程序会创建 Agent，依次创建 sandbox、打开 `https://example.com`、保存截图，然后进入交互模式。输入 `quit`、`exit` 或按 Ctrl+C/Ctrl+D 结束，sandbox 会被销毁。

## 配置

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `E2B_API_KEY` | 是 | E2B API Key。 |
| `E2B_API_URL` / `E2B_DOMAIN` | 否 | E2B-compatible 区域部署需要的 API 端点与域名。 |
| `E2B_BROWSER_IMAGE` | 否 | 用于构建临时浏览器模板的镜像；默认使用项目内置镜像。 |
| `E2B_TIMEOUT` | 否 | Sandbox 生命周期超时秒数，默认 `600`。 |
| `OPENAI_API_KEY` | 是 | OpenAI-compatible 服务的 API Key。 |
| `OPENAI_BASE_URL` | 否 | OpenAI-compatible API 基础 URL；OpenAI 默认 `https://api.openai.com/v1`。 |
| `OPENAI_MODEL` | 否 | 模型名，默认 `gpt-4o-mini`。 |

## 工具

| Tool | 作用 |
| --- | --- |
| `create_browser_sandbox` | 创建或复用 E2B sandbox，启动 browsertool。 |
| `get_sandbox_info` | 返回 sandbox ID、CDP 地址和模板名。 |
| `navigate_to_url` | 通过带认证头的 CDP 连接访问网页。 |
| `browser_screenshot` | 将当前页 PNG 截图保存到 `screenshots/`。 |
| `destroy_sandbox` | 销毁 sandbox、释放资源。 |

## 项目结构

```text
e2b-browser-langchain/
├── main.py              # 演示与交互式入口
├── langchain_agent.py   # Agent 和浏览器工具
├── sandbox_manager.py   # E2B 模板、sandbox、browsertool 和 CDP 生命周期
├── env.example          # 配置示例
└── requirements.txt     # Python 依赖
```

## 运行机制

1. `SandboxManager` 从 `E2B_BROWSER_IMAGE` 构建临时模板，再使用该模板创建 sandbox。
2. 管理器在 sandbox 内启动 browsertool，并轮询 `http://localhost:3000/health`。
3. 通过 `sandbox.get_host(3000)` 得到公开 host，组成 `/ws/automation` CDP WebSocket 地址。
4. Playwright 使用 `X-Access-Token` 认证头调用 `connect_over_cdp`。
5. 程序退出时调用 `sandbox.kill()`。

浏览器截图是本 demo 的可观测输出；它不依赖额外的远程桌面服务。
