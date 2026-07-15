# Browser Studio E2B

[English](README.md)

Browser Studio 是一个面向阿里云 E2B 浏览器沙箱的自动化 demo。它提供基于 Vite +
React 的专业化前端界面，通过 SSE 实时展示运行事件，并在后端完成 E2B sandbox
生命周期管理、Playwright CDP 浏览器导航和整页截图。

## 当前能力

- 提交包含完整 `http://` 或 `https://` URL 的浏览器任务。
- 为每次运行创建隔离的 E2B browser sandbox。
- 在 sandbox 内启动 browsertool，并通过 CDP 连接浏览器。
- 使用 Playwright 导航页面并采集整页 PNG 截图。
- 通过 SSE 将后端进度实时推送到前端。
- 停止运行并销毁对应 sandbox。

当前版本聚焦 URL 导航和截图。VNC 与 human-in-the-loop 控制暂未包含在本版本中。

## 技术栈

- 后端：FastAPI、Uvicorn、E2B SDK、Playwright。
- 前端：Vite、React 18、TypeScript、Tailwind CSS、shadcn 风格组件、
  lucide-react 图标。
- 测试：pytest、pytest-asyncio、httpx。

## 目录边界

- `src/core/`：运行配置、run 生命周期、事件和共享状态。
- `src/browser/`：E2B sandbox 创建、browsertool 启动、CDP 自动化、截图采集和
  API 路由。
- `web/`：基于 Vite、Tailwind CSS 和 shadcn 约定的 Browser Studio 前端。
- `tests/`：后端单元测试与 API 集成测试。
- `contexts/`：本地 agent / self-improvement 上下文文件。

## 本地启动

前置条件：Python 3.12+、Node.js 20+，以及可访问 E2B 的凭据。

启动后端：

```bash
cp env.example .env
# 编辑 .env，填写 E2B_API_KEY、E2B_API_URL 和 E2B_DOMAIN
uv sync --extra dev
uv run studio
```

另开一个终端启动前端：

```bash
cd web
npm install
npm run dev
```

打开 <http://localhost:5173>。Vite dev server 会将 `/api` 和 `/health` 代理到
<http://127.0.0.1:8000>。后端 API 文档位于
<http://127.0.0.1:8000/docs>。

## 配置

后端从仓库根目录的 `.env` 读取配置。常用配置项：

- `E2B_API_KEY`：必填，阿里云 E2B API key。
- `E2B_API_URL`：必填，阿里云 E2B API URL。
- `E2B_DOMAIN`：必填，阿里云 E2B Sandbox 域名。
- `E2B_TEMPLATE`：可选，预先构建好的 browser template 名称。
- `E2B_BROWSER_IMAGE`：未设置 template 时用于构建临时 template 的浏览器镜像。
- `E2B_TIMEOUT`：sandbox 超时时间，单位秒。
- `STUDIO_HOST` / `STUDIO_PORT`：后端监听地址。
- `STUDIO_CORS_ORIGINS`：允许访问后端的前端 origin，多个值用逗号分隔。

如果未设置 `E2B_TEMPLATE`，服务会先基于 `E2B_BROWSER_IMAGE` 构建一个临时浏览器
template，再创建 sandbox。对于重复 demo 或接近生产的使用方式，建议预先创建
template 并设置 `E2B_TEMPLATE`，避免每次启动都构建。

## 前端命令

在 `web/` 目录执行：

```bash
npm run dev      # 启动 Vite
npm run build    # TypeScript 检查并构建生产资源
npm run preview  # 预览生产构建
```

前端已包含 `components.json`、Tailwind 配置，以及 shadcn 风格的
`src/lib/utils.ts` 工具函数，后续可以按同一约定继续添加 shadcn 组件。

## API

- `POST /api/runs`：提交任务。任务中必须包含完整的 `http(s)` URL；服务会提取
  第一个 URL，导航并截图。
- `GET /api/runs/{id}`：读取 run 状态与结果元数据。
- `GET /api/runs/{id}/events`：SSE 实时事件流。
- `GET /api/runs/{id}/screenshot`：获取最新 PNG 截图。
- `DELETE /api/runs/{id}`：停止运行并销毁对应 E2B sandbox。

## 验证

后端测试：

```bash
uv run pytest
```

前端构建：

```bash
cd web
npm run build
```
