import pytest

from src.browser.service import task_url


def test_extracts_url_from_chinese_task():
    assert task_url("打开 https://example.com/path?x=1 并截图") == "https://example.com/path?x=1"


def test_rejects_task_without_url():
    with pytest.raises(ValueError, match="URL"):
        task_url("帮我搜索一下天气")
