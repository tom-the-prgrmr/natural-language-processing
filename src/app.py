"""FastAPI demo: 1 endpoint /chat bọc src/generation.py.

Chạy: .venv/Scripts/uvicorn src.app:app --reload --port 8000
Giữ Retriever + OpenAI client dùng chung giữa các request (tải index 1 lần
lúc khởi động) thay vì tạo mới mỗi câu hỏi -- tránh gọi lại embedding corpus.
"""

import os
import threading
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAIError
from pydantic import BaseModel

from src.generation import AnswerResult, Turn, answer
from src.generation import _client as generation_client
from src.retrieval import Retriever

WEB_DIR = Path("web")
_state: dict = {}


class RateLimiter:
    """Giới hạn request /chat để link công khai không đốt hết tiền API.

    0 = tắt (mặc định khi chạy local). Giới hạn theo ngày là chặn cứng tổng
    chi phí; giới hạn theo IP chỉ để một người không chiếm hết hạn mức ngày
    (IP lấy từ X-Forwarded-For nên có thể bị giả, không dùng để bảo mật).
    Bộ nhớ trong tiến trình — đủ cho 1 instance, mất khi khởi động lại.
    """

    def __init__(self, per_minute: int = 0, daily: int = 0):
        self.per_minute = per_minute
        self.daily = daily
        self._hits: dict[str, deque] = defaultdict(deque)
        self._day = ""
        self._day_count = 0
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> str | None:
        """Trả None nếu cho qua, hoặc thông báo lỗi tiếng Việt nếu vượt giới hạn."""
        now = time.time() if now is None else now
        with self._lock:
            day = time.strftime("%Y-%m-%d", time.gmtime(now))
            if day != self._day:
                self._day, self._day_count = day, 0
            if self.daily and self._day_count >= self.daily:
                return "Bản demo đã hết lượt hỏi trong hôm nay, vui lòng quay lại ngày mai."
            hits = self._hits[key]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            if self.per_minute and len(hits) >= self.per_minute:
                return "Bạn hỏi hơi nhanh, vui lòng đợi khoảng một phút rồi hỏi tiếp."
            hits.append(now)
            self._day_count += 1
            return None


_limiter = RateLimiter(
    per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "0")),
    daily=int(os.getenv("DAILY_REQUEST_LIMIT", "0")),
)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _state["started_at"] = time.time()
    try:
        _state["retriever"] = Retriever()
        _state["client"] = generation_client()
    except OpenAIError as e:
        # Lỗi phổ biến nhất khi mới cài đặt: thiếu/sai OPENAI_API_KEY trong
        # .env. Không bắt được lỗi này thì uvicorn chỉ in traceback sâu từ
        # bên trong thư viện openai, khó biết nguyên nhân thật.
        raise RuntimeError(
            "Không khởi động được server: lỗi cấu hình/kết nối OpenAI API. "
            "Kiểm tra OPENAI_API_KEY (file .env khi chạy local, xem .env.example; "
            "biến môi trường của service khi deploy)."
        ) from e
    yield
    _state.clear()


app = FastAPI(title="Chatbot tra cứu mức phạt giao thông", lifespan=_lifespan)

# Demo cục bộ, không có cookie/credential -- cho phép mọi origin để trang
# web/index.html vẫn gọi được /chat kể cả khi mở trực tiếp (file://) hoặc
# phục vụ từ một static server khác (port khác với uvicorn).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatTurn] = []


class ChatResponse(BaseModel):
    answer: str
    citations: list[str]
    refused: bool
    needs_clarification: bool
    clarify_question: str | None
    retrieved_ids: list[str]
    hallucinated_citations: list[str]
    ungrounded_amounts: list[str]
    citation_labels: list[str]
    retrieval_ms: float
    generation_ms: float


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    limited = _limiter.check(_client_key(request))
    if limited:
        raise HTTPException(status_code=429, detail=limited)
    history = [Turn(role=t.role, content=t.content) for t in req.history]
    try:
        r: AnswerResult = answer(
            req.question,
            history=history,
            retriever=_state["retriever"],
            client=_state["client"],
        )
    except OpenAIError as e:
        # Không để lộ stack trace/chi tiết lỗi API ra ngoài -- trả 503 kèm
        # thông báo tiếng Việt dễ hiểu, người dùng demo thử lại sau được.
        raise HTTPException(
            status_code=503,
            detail="Hệ thống đang gặp sự cố khi gọi dịch vụ AI, vui lòng thử lại sau.",
        ) from e
    return ChatResponse(
        answer=r.answer,
        citations=r.citations,
        refused=r.refused,
        needs_clarification=r.needs_clarification,
        clarify_question=r.clarify_question,
        retrieved_ids=r.retrieved_ids,
        hallucinated_citations=r.hallucinated_citations,
        ungrounded_amounts=r.ungrounded_amounts,
        citation_labels=r.citation_labels,
        retrieval_ms=r.retrieval_ms,
        generation_ms=r.generation_ms,
    )


@app.get("/health")
def health() -> dict:
    # uptime_s nhỏ hơn thời gian vừa phải chờ => server vừa khởi động lại
    # (bản deploy miễn phí tự ngủ khi không ai dùng); web dùng để báo người dùng.
    uptime = time.time() - _state.get("started_at", time.time())
    return {
        "status": "ok",
        "chunks": len(_state["retriever"].chunks),
        "uptime_s": round(uptime, 1),
    }


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
