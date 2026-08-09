"""Configuration for the BrowserUse + E2B demo."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    """Runtime settings read from the environment."""

    e2b_api_key: str = Field(default_factory=lambda: os.getenv("E2B_API_KEY", ""))
    e2b_api_url: str = Field(default_factory=lambda: os.getenv("E2B_API_URL", ""))
    e2b_domain: str = Field(default_factory=lambda: os.getenv("E2B_DOMAIN", ""))
    e2b_template: str = Field(default_factory=lambda: os.getenv("E2B_TEMPLATE", ""))
    e2b_timeout: int = Field(default_factory=lambda: int(os.getenv("E2B_TIMEOUT", "600")))
    e2b_browser_image: str = Field(default_factory=lambda: os.getenv("E2B_BROWSER_IMAGE", "fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.44"))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = Field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    browser_use_vision: bool = Field(default_factory=lambda: os.getenv("BROWSER_USE_VISION", "true").lower() == "true")
    user_agent: str = Field(default_factory=lambda: os.getenv("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
