"""Small, local helpers shared by the BrowserUse examples."""

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def setup_example_environment() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_logger(session_id: str) -> logging.Logger:
    logger = logging.getLogger(f"browseruse.{session_id}")
    logger.setLevel(logging.INFO)
    return logger


def validate_settings(settings: object) -> bool:
    missing = [name for name in ("E2B_API_KEY", "OPENAI_API_KEY") if not os.getenv(name)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        return False
    return True


def print_section(title: str) -> None:
    print(f"\n{'=' * 64}\n{title}\n{'=' * 64}")


def print_info(label: str, value: object) -> None:
    print(f"  {label}: {value}")


def print_result(result: object) -> None:
    print(f"\n{'-' * 64}\n{result}\n{'-' * 64}")


def print_execution_stats(result: object) -> None:
    try:
        print_info("Steps", len(result.model_thoughts()))
    except Exception:
        pass


def get_env_or_default(key: str, default: str) -> str:
    return os.getenv(key, default)
