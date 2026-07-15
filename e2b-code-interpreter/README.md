# E2B Code Interpreter Demo

[中文文档](README_ZH-CN.md)

A minimal Alibaba Cloud E2B Code Interpreter SDK demo: create a sandbox, run Python code inside it, and tear it down.

## What it does

1. **Creates a sandbox** — an isolated cloud environment running a Python interpreter.
2. **Computes circle area** — runs Python code to calculate the area of a circle with radius 5.
3. **Computes circumference** — runs more code in the same sandbox, demonstrating state persistence by reading the radius saved by the first execution.
4. **Kills the sandbox** — releases all resources.

## Quick start

```bash
# 1. Set up a virtual environment
uv venv .venv --python 3.12
source .venv/bin/activate

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Configure environment variables
cp env.example .env
# Edit .env and fill in E2B_API_KEY, E2B_API_URL, and E2B_DOMAIN.

# 4. Run the demo
python code_exec.py
```

## Environment variables

The E2B SDK reads these automatically — no need to pass them explicitly in code.

| Variable | Required | Description |
|---|---|---|
| `E2B_API_KEY` | Yes | Alibaba Cloud E2B API key |
| `E2B_API_URL` | Yes | Alibaba Cloud E2B control-plane API URL |
| `E2B_DOMAIN` | Yes | Alibaba Cloud E2B sandbox domain |

## SDK usage (minimal)

```python
from e2b_code_interpreter import Sandbox

sbx = Sandbox.create()
execution = sbx.run_code("""
import math
radius = 5
area = math.pi * radius ** 2
print(f"Area: {area:.2f}")
""")
print(execution.logs.stdout)
sbx.kill()
```

## Project structure

```
e2b-code-interpreter/
├── code_exec.py      # Main demo script (~50 lines)
├── env.example       # Template for .env
├── pyproject.toml    # Project metadata and dependencies
├── requirements.txt  # Pinned dependencies
└── README.md
```
