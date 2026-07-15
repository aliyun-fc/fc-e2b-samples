# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260714-010] best_practice

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: high
**Status**: pending
**Area**: backend

### Summary
When a synchronous E2B sandbox manager is called from BrowserUse async code, Playwright Sync API probes must run in a worker thread.

### Details
BrowserUse starts agents in an active asyncio loop. Calling `sync_playwright()` on that loop raises an explicit Playwright error. Running the short authenticated CDP readiness probe in a `ThreadPoolExecutor` preserves the synchronous manager API and prevents nested-loop failures.

### Suggested Action
Run a real E2B BrowserUse smoke test after the thread-based probe change; retain the isolated unit test to protect the async/sync boundary.

### Metadata
- Source: error
- Related Files: e2b-browser-use/examples/sandbox_manager.py, e2b-browser-use/tests/test_sandbox_manager.py
- Tags: playwright, browser-use, e2b, asyncio, cdp

---

## [LRN-20260714-001] best_practice

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
BrowserUse can attach to an authenticated remote E2B CDP endpoint with `cdp_url`, `headers`, and `is_local=False`.

### Details
The E2B browsertool integration exposes CDP at `wss://{sandbox.get_host(3000)}/ws/automation` and requires the `X-Access-Token` header. The installed BrowserUse constructor accepts all three remote-connection arguments, allowing the E2B browser sandbox to be used without a local browser or a VNC bridge.

### Suggested Action
Keep a signature-level compatibility check when upgrading BrowserUse; the E2B SDK token is currently obtained from `_envd_access_token`, which is not a public API.

### Metadata
- Source: conversation
- Related Files: browseruse-e2b-demo/examples/sandbox_manager.py
- Tags: e2b, browseruse, cdp, authentication

---

## [LRN-20260714-002] insight

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
An E2B browser product can avoid per-run image builds when it is provisioned with a prebuilt template that exposes browsertool endpoints.

### Details
Sandbox Studio's Browser E2B backend creates a configured browser template directly, derives the public port-3000 host, and connects to `/ws/automation` for CDP (and `/ws/liveview` for optional live view). This contrasts with the standalone demos, which build a temporary template from an image and start browsertool in the sandbox. Both require `X-Access-Token` from the sandbox's `_envd_access_token`.

### Suggested Action
For production-like demos, prefer `E2B_TEMPLATE` to avoid build latency; retain the image-build fallback only when self-contained setup is the priority.

### Metadata
- Source: conversation
- Related Files: sandbox-studio/src/products/cloud_sandbox/browser/backend.py
- Tags: e2b, browsertool, templates, cdp

---

## [LRN-20260714-003] best_practice

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
Product deletion in Sandbox Studio must start with framework and route registration, not package removal alone.

### Details
`src/core/frameworks.py` imports all product families and lazily imports the AgentRun custom-image registry. `src/main.py` mounts routers for every platform. Removing an unused backend package without replacing these registration points leaves startup imports and API routes coupled to the removed implementation.

### Suggested Action
For a focused E2B Browser edition, explicitly register only `browser-e2b:langchain` and `browser-e2b:browseruse`, and mount only the Browser E2B routes before deleting other packages.

### Metadata
- Source: conversation
- Related Files: sandbox-studio/src/core/frameworks.py
- Tags: architecture, e2b, routing, dependency-pruning

---

## [LRN-20260714-004] insight

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: high
**Status**: resolved
**Area**: docs

### Summary
`pause-resume-demo` is currently a duplicate Code Interpreter quickstart, not a pause/resume demonstration.

### Details
Its README and `code_exec.py` contain the same create, execute twice with persisted state, and kill workflow as `code-interpreter-demo`; no pause or reconnect behavior is implemented. A rename would misrepresent its capability.

### Suggested Action
Remove the duplicate directory, or implement an actual pause/resume workflow before publishing it as a separate demo.

### Metadata
- Source: conversation
- Related Files: pause-resume-demo/code_exec.py
- Tags: demos, duplication, naming

### Resolution
- **Resolved**: 2026-07-14T00:00:00+08:00
- **Notes**: Removed the duplicate `pause-resume-demo` directory.

---

## [LRN-20260714-005] knowledge_gap

**Logged**: 2026-07-14T00:00:00+08:00
**Priority**: medium
**Status**: pending
**Area**: config

### Summary
The E2B LangChain Code Interpreter cookbook notebook demonstrates the desired architecture but uses legacy LangChain APIs.

### Details
The notebook wraps a long-lived `e2b_code_interpreter.Sandbox` as a Python-code tool, but imports older agent output-parser APIs and `pydantic.v1`. A new demo should keep the tool lifecycle while using the installed modern LangChain agent and tool interfaces.

### Suggested Action
Implement the example as a modernized demo with explicit sandbox cleanup and current LangChain dependencies; do not copy notebook imports unchanged.

### Metadata
- Source: conversation
- Related Files: e2b-pdf-to-markdown-langchain/pyproject.toml
- Tags: e2b, langchain, code-interpreter, compatibility

---
