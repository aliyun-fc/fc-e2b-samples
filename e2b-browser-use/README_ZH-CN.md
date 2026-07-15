# BrowserUse + E2B Browser Sandbox 示例

[English](README.md)

在阿里云 E2B 浏览器 Sandbox 中运行 [BrowserUse](https://github.com/browser-use/browser-use)
Agent。示例会在 Sandbox 内启动 `browsertool`，并通过携带 E2B 访问令牌的 Chrome
DevTools Protocol（CDP）端点连接 BrowserUse。它包含基础任务以及多任务会话复用示例。

## 运行

```bash
cd e2b-browser-use
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

cp env.example .env
# 在 .env 中设置 E2B_API_KEY、E2B_API_URL、E2B_DOMAIN 和模型服务商变量。

python examples/01_browseruse_basic.py
python examples/02_browseruse_advanced.py
```

无需本地浏览器服务或第二个终端。

## 验证本地生命周期逻辑

测试使用 fake 而非真实 E2B 账号，因此不会创建 Sandbox，也不需要 API Key：

```bash
python -m unittest discover -s tests -v
```

测试覆盖已认证 CDP 端点构造、初始化失败后的清理、会话复用，以及安全替换已有会话。

## 配置

| 变量 | 必填 | 用途 |
| --- | --- | --- |
| `E2B_API_KEY` | 是 | 阿里云 E2B API Key。 |
| `E2B_API_URL` | 是 | 阿里云 E2B API URL。 |
| `E2B_DOMAIN` | 是 | 阿里云 E2B Sandbox 域名。 |
| `E2B_TEMPLATE` | 否 | 要复用的已有浏览器模板。 |
| `E2B_BROWSER_IMAGE` | 否 | 未设置模板时用于构建临时模板的镜像。 |
| `E2B_TIMEOUT` | 否 | Sandbox 生命周期秒数；默认 `600`。 |
| `OPENAI_API_KEY` | 是 | OpenAI-compatible Chat Completions 服务商的 API Key。 |
| `OPENAI_BASE_URL` | 否 | 服务商基础 URL；默认 OpenAI。 |
| `OPENAI_MODEL` | 否 | 模型名称；默认 `gpt-4.1-mini`。 |

## 工作方式

1. `SandboxManager` 从 `E2B_TEMPLATE` 创建 E2B Sandbox，或从 `E2B_BROWSER_IMAGE` 构建临时模板。
2. 它启动 `browsertool` 并等待健康检查端点就绪。
3. 它从 E2B 获取 browsertool host，并返回 CDP WebSocket URL 和 `X-Access-Token` 请求头。
4. `Browser(..., cdp_url=..., headers=..., is_local=False)` 将 BrowserUse 连接到远程浏览器。
5. 示例在 `finally` 块中停止 BrowserUse 并删除 E2B Sandbox。

`examples/runner.py` 会在 Python 进程内按 `(user_id, session_id, thread_id)` 缓存活跃
Sandbox。使用相同值再次调用 `create_or_get_sandbox` 将复用现有浏览器会话。

## 排障

- **缺少环境变量**：将 `env.example` 复制为 `.env`，然后设置 `E2B_API_KEY`、`E2B_API_URL`、`E2B_DOMAIN` 和 `OPENAI_API_KEY`。
- **browsertool 未就绪**：确认浏览器镜像可被 E2B 部署访问；抛出的错误包含 browsertool 进程日志末尾。
- **CDP 认证错误**：使用支持远程浏览器 `headers` 选项的 BrowserUse 版本；依赖文件已锁定兼容范围。
