"""Test FastAPI /chat -- không gọi OpenAI thật, mock toàn bộ.

TestClient khởi tạo không dùng `with` nên không chạy `lifespan` thật (không
gọi Retriever() -> embedding API thật): set `_state` trực tiếp và patch
src.app.answer thay vì để request đi qua Retriever/OpenAI client thật.
"""

import asyncio
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from openai import OpenAIError

import src.app as app_module
from src.app import RateLimiter
from src.generation import AnswerResult

client = TestClient(app_module.app)
app_module._state["retriever"] = object()
app_module._state["client"] = object()


def test_chat_returns_503_with_friendly_message_on_openai_error():
    with patch("src.app.answer", side_effect=OpenAIError("boom")):
        res = client.post("/chat", json={"question": "abc", "history": []})
    assert res.status_code == 503
    assert "sự cố" in res.json()["detail"]


def test_health_reports_chunk_count_and_uptime():
    app_module._state["retriever"] = type("R", (), {"chunks": [1, 2, 3]})()
    app_module._state["started_at"] = time.time() - 100
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["chunks"] == 3
    assert 99 <= body["uptime_s"] <= 105


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


def test_rate_limiter_is_off_by_default():
    limiter = RateLimiter()
    assert all(limiter.check("ip", now=0) is None for _ in range(100))


def test_rate_limiter_per_minute_is_per_ip_and_window_slides():
    limiter = RateLimiter(per_minute=2)
    assert limiter.check("a", now=0) is None
    assert limiter.check("a", now=1) is None
    assert "đợi" in limiter.check("a", now=2)
    assert limiter.check("b", now=2) is None  # IP khác không bị ảnh hưởng
    assert limiter.check("a", now=61) is None  # đã qua cửa sổ 60 giây


def test_rate_limiter_daily_cap_is_global_and_resets_next_day():
    limiter = RateLimiter(daily=2)
    assert limiter.check("a", now=0) is None
    assert limiter.check("b", now=10) is None
    assert "hôm nay" in limiter.check("c", now=20)  # chặn cả IP mới
    assert limiter.check("c", now=86400) is None  # sang ngày mới (UTC)


def test_chat_returns_429_with_message_when_rate_limited():
    fake = AnswerResult(
        answer="ok",
        citations=[],
        refused=False,
        needs_clarification=False,
        clarify_question=None,
    )
    with (
        patch.object(app_module, "_limiter", RateLimiter(per_minute=1)),
        patch("src.app.answer", return_value=fake),
    ):
        first = client.post("/chat", json={"question": "abc", "history": []})
        second = client.post("/chat", json={"question": "abc", "history": []})
    assert first.status_code == 200
    assert second.status_code == 429
    assert "đợi" in second.json()["detail"]
