# Browser Studio E2B

[English](README.md)

一个仅面向 E2B 浏览器沙箱的精简 Studio。第一阶段保留任务提交、SSE
事件、CDP 浏览器自动化和截图；VNC 与 HITL 将在基础运行链路稳定后再加入。

## 目录边界

- `src/core/`：run 生命周期、SSE、会话和共享类型。
- `src/browser/`：E2B backend、CDP、BrowserUse、LangChain 与 API 路由。
- `web/`：单一 Browser Studio 前端。
- `tests/`：后端单元与 API 集成测试。
- `docs/`：架构决策与接口说明。

## 本地启动

前置条件：Python 3.12+、Node.js 20+，以及可访问 E2B 的凭据。

```bash
cp env.example .env
# 编辑 .env，至少填写 E2B_API_KEY
uv sync --extra dev
uv run studio
```

另开一个终端启动前端：

```bash
cd web
npm install
npm run dev
```

打开 <http://localhost:5173>。后端 API 文档位于
<http://127.0.0.1:8000/docs>。

首次运行若未设置 `E2B_TEMPLATE`，服务会以 `E2B_BROWSER_IMAGE` 创建一个临时
浏览器模板；生产环境建议预先创建模板并设置 `E2B_TEMPLATE`，可避免每次创建开销。

## API

- `POST /api/runs`：提交任务。任务中需包含完整的 `http(s)` URL，服务会导航并截图。
- `GET /api/runs/{id}/events`：SSE 实时事件流。
- `GET /api/runs/{id}/screenshot`：获取最新截图。
- `DELETE /api/runs/{id}`：销毁对应 E2B sandbox。
