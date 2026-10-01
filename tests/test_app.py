"""Test FastAPI /chat -- không gọi OpenAI thật, mock toàn bộ.

TestClient khởi tạo không dùng `with` nên không chạy `lifespan` thật (không
gọi Retriever() -> embedding API thật): set `_state` trực tiếp và patch
src.app.answer thay vì để request đi qua Retriever/OpenAI client thật.
"""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from openai import OpenAIError

import src.app as app_module

client = TestClient(app_module.app)
app_module._state["retriever"] = object()
app_module._state["client"] = object()


def test_chat_returns_503_with_friendly_message_on_openai_error():
    with patch("src.app.answer", side_effect=OpenAIError("boom")):
        res = client.post("/chat", json={"question": "abc", "history": []})
    assert res.status_code == 503
    assert "sự cố" in res.json()["detail"]


def test_health_reports_chunk_count():
    app_module._state["retriever"] = type("R", (), {"chunks": [1, 2, 3]})()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "chunks": 3}


def test_startup_failure_on_bad_api_key_is_a_clear_runtime_error():
    # Lỗi phổ biến nhất khi mới cài đặt (thiếu/sai OPENAI_API_KEY) phải dừng
    # server với thông báo rõ ràng, không phải traceback sâu từ thư viện openai.
    class FakeRetriever:
        def __init__(self):
            raise OpenAIError("invalid api key (gia lap)")

    async def run():
        with patch("src.app.Retriever", FakeRetriever):
            async with app_module._lifespan(app_module.app):
                pass

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY") as exc_info:
        asyncio.run(run())
    assert isinstance(exc_info.value.__cause__, OpenAIError)
