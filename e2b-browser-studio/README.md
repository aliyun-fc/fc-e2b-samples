# Browser Studio E2B

[中文文档](README_ZH-CN.md)

Browser Studio is a focused demo for running browser automation inside Alibaba Cloud E2B
sandboxes. It provides a polished Vite + React frontend, live run events over
SSE, E2B sandbox lifecycle management, Playwright-over-CDP navigation, and
full-page screenshots.

## What it does

- Submit a browser task that contains a complete `http://` or `https://` URL.
- Create an isolated E2B browser sandbox for the run.
- Start the browsertool process inside the sandbox and connect through CDP.
- Navigate with Playwright and capture a full-page screenshot.
- Stream backend progress events to the UI in real time.
- Stop an active run and destroy the associated sandbox.

The current demo focuses on URL navigation and screenshots. VNC and
human-in-the-loop controls are not part of this version.

## Tech stack

- Backend: FastAPI, Uvicorn, E2B SDK, Playwright.
- Frontend: Vite, React 18, TypeScript, Tailwind CSS, shadcn-style components,
  lucide-react icons.
- Tests: pytest, pytest-asyncio, httpx.

## Directory boundaries

- `src/core/`: runtime settings, run lifecycle, events, and shared state.
- `src/browser/`: E2B sandbox creation, browsertool startup, CDP automation,
  screenshot capture, and API routes.
- `web/`: Browser Studio frontend built with Vite, Tailwind CSS, and shadcn
  conventions.
- `tests/`: backend unit tests and API integration tests.
- `contexts/`: local agent/self-improvement context files.

## Run locally

Prerequisites: Python 3.12+, Node.js 20+, and credentials that can access E2B.

Set up the backend:

```bash
cp env.example .env
# Edit .env and set E2B_API_KEY, E2B_API_URL, and E2B_DOMAIN.
uv sync --extra dev
uv run studio
```

Start the frontend in another terminal:

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/health`
to the backend at <http://127.0.0.1:8000>. Backend API documentation is
available at <http://127.0.0.1:8000/docs>.

## Configuration

The backend reads `.env` from the repository root. Common settings:

- `E2B_API_KEY`: required Alibaba Cloud E2B API key.
- `E2B_API_URL`: required Alibaba Cloud E2B API URL.
- `E2B_DOMAIN`: required Alibaba Cloud E2B sandbox domain.
- `E2B_TEMPLATE`: optional prebuilt browser template name.
- `E2B_BROWSER_IMAGE`: browser image used when building a temporary template.
- `E2B_TIMEOUT`: sandbox timeout in seconds.
- `STUDIO_HOST` / `STUDIO_PORT`: backend bind address.
- `STUDIO_CORS_ORIGINS`: comma-separated allowed frontend origins.

When `E2B_TEMPLATE` is not set, the service builds a temporary browser template
from `E2B_BROWSER_IMAGE` before creating a sandbox. For repeated demos or
production-like usage, create a template in advance and set `E2B_TEMPLATE` to
avoid rebuilding it on startup.

## Frontend commands

Run from `web/`:

```bash
npm run dev      # start Vite
npm run build    # type-check and build production assets
npm run preview  # preview the production build
```

The frontend includes `components.json`, Tailwind config, and the shadcn-style
`src/lib/utils.ts` helper so new shadcn components can be added consistently.

## API

- `POST /api/runs`: submit a task. The task must contain a complete `http(s)`
  URL; the service extracts the first URL, navigates to it, and captures a
  screenshot.
- `GET /api/runs/{id}`: read run status and result metadata.
- `GET /api/runs/{id}/events`: stream real-time run events over SSE.
- `GET /api/runs/{id}/screenshot`: return the latest PNG screenshot.
- `DELETE /api/runs/{id}`: stop the run and destroy the associated E2B sandbox.

## Validation

Backend tests:

```bash
uv run pytest
```

Frontend build:

```bash
cd web
npm run build
```
