# Changelog - 2026-07-05

## Summary
Fix browser_sandbox_demo.py not reading env vars from .env, causing the SDK to miss the us-west-1 region.

## Changes
- `load_dotenv` now resolves `.env` relative to the script path and uses `override=True` to override same-named shell env vars
- Remove hardcoded `E2B_DOMAIN` / `E2B_API_URL` from code; fully driven by `.env`
- Update README.md with correct run command and env var table

## Related Files
- `browser_sandbox_demo.py`
- `README.md`
- `.env`

## Test
- Run `uv run browser_sandbox_demo.py` to verify template build and sandbox creation hit us-west-1 region, Playwright CDP verification passes
