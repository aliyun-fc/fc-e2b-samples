import pytest

from src.browser.service import BrowserService, task_url
from src.core.runs import RunStore
from src.core.settings import Settings


def test_extracts_url_from_chinese_task():
    assert task_url("打开 https://example.com/path?x=1 并截图") == "https://example.com/path?x=1"


def test_rejects_task_without_url():
    with pytest.raises(ValueError, match="URL"):
        task_url("帮我搜索一下天气")


def test_create_sandbox_passes_domain_to_template_build_and_sandbox_create(monkeypatch):
    calls = {}

    class FakeTemplate:
        def from_image(self, image):
            calls["image"] = image
            return self

        @staticmethod
        def build(template, name, **kwargs):
            calls["template_build"] = kwargs

            class BuildInfo:
                name = "built-template"

            return BuildInfo()

    class FakeSandbox:
        sandbox_id = "sandbox-id"

        @staticmethod
        def create(**kwargs):
            calls["sandbox_create"] = kwargs
            return FakeSandbox()

    class FakeE2B:
        Template = FakeTemplate
        Sandbox = FakeSandbox

    monkeypatch.setitem(__import__("sys").modules, "e2b", FakeE2B)
    settings = Settings(
        e2b_api_key="test-key",
        e2b_api_url="https://api.test",
        e2b_domain="sandbox.test",
        e2b_browser_image="browser-image",
    )

    sandbox, template = BrowserService(settings, RunStore())._create_sandbox()

    assert sandbox.sandbox_id == "sandbox-id"
    assert template == "built-template"
    assert calls["template_build"]["api_key"] == "test-key"
    assert calls["template_build"]["api_url"] == "https://api.test"
    assert calls["template_build"]["domain"] == "sandbox.test"
    assert calls["sandbox_create"]["api_key"] == "test-key"
    assert calls["sandbox_create"]["api_url"] == "https://api.test"
    assert calls["sandbox_create"]["domain"] == "sandbox.test"
