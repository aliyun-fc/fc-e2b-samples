"""E2B Code Interpreter Sandbox — minimal demo.

Mirrors the official quickstart (https://e2b.dev/docs/quickstart):
  1. Create a sandbox
  2. Run Python code inside it (compute circle area)
  3. Run more code with sandbox state persistence (compute circumference)
  4. Kill the sandbox

The E2B SDK reads E2B_API_KEY, E2B_DOMAIN, and E2B_API_URL from
environment variables automatically.
"""

import os

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

load_dotenv()


def require_alibaba_e2b_env() -> None:
    missing = [
        name
        for name in ("E2B_API_KEY", "E2B_API_URL", "E2B_DOMAIN")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Alibaba Cloud E2B requires environment variables: " + ", ".join(missing)
        )


def main() -> None:
    require_alibaba_e2b_env()
    # 1. Create sandbox
    print("Creating sandbox...")
    sbx = Sandbox.create()
    print(f"Sandbox created: {sbx.sandbox_id}\n")

    try:
        # 2. Compute circle area
        # Imports are inside the function to avoid module-level variables
        # that the sandbox cannot serialize (pickle) between executions.
        print("Computing circle area...")
        execution = sbx.run_code("""
def compute_area():
    import math
    radius = 5
    area = math.pi * radius ** 2
    print(f"Circle with radius {radius}: area = {area:.2f}")
    return radius

radius = compute_area()
from pathlib import Path
Path("/tmp/radius.txt").write_text(str(radius))
""")
        print(f"stdout: {execution.logs.stdout}")

        # 3. Compute circumference — state persists across executions
        print("\nComputing circumference (state persists)...")
        execution = sbx.run_code("""
def compute_circumference():
    import math
    from pathlib import Path
    radius = float(Path("/tmp/radius.txt").read_text())
    circumference = 2 * math.pi * radius
    print(f"Circle with radius {radius:.0f}: circumference = {circumference:.2f}")

compute_circumference()
""")
        print(f"stdout: {execution.logs.stdout}")

    finally:
        # 4. Kill the sandbox
        sbx.kill()
        print(f"\nSandbox stopped: {sbx.sandbox_id}")


if __name__ == "__main__":
    main()
