# Browser Studio E2B

[中文文档](README_ZH-CN.md)

A focused Studio for E2B browser sandboxes. The first phase provides task
submission, SSE events, CDP browser automation, and screenshots. VNC and
human-in-the-loop features will be added after the core runtime flow is stable.

## Directory boundaries

- `src/core/`: run lifecycle, SSE, sessions, and shared types.
- `src/browser/`: E2B backend, CDP, BrowserUse, LangChain, and API routes.
- `web/`: the Browser Studio frontend.
- `tests/`: backend unit and API integration tests.
- `docs/`: architecture decisions and API documentation.

## Run locally

Prerequisites: Python 3.12+, Node.js 20+, and credentials that can access E2B.

```bash
cp env.example .env
# Edit .env and set at least E2B_API_KEY.
uv sync --extra dev
uv run studio
```

Start the frontend in another terminal:

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. Backend API documentation is available at
<http://127.0.0.1:8000/docs>.

When `E2B_TEMPLATE` is not set on the first run, the service builds a temporary
browser template from `E2B_BROWSER_IMAGE`. For production, create a template in
advance and set `E2B_TEMPLATE` to avoid rebuilding it for each startup.

## API

- `POST /api/runs`: submit a task containing a complete `http(s)` URL; the service navigates to it and captures a screenshot.
- `GET /api/runs/{id}/events`: stream real-time events over SSE.
- `GET /api/runs/{id}/screenshot`: return the latest screenshot.
- `DELETE /api/runs/{id}`: destroy the associated E2B sandbox.
