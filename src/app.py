"""FastAPI demo: 1 endpoint /chat bọc src/generation.py.

Chạy: .venv/Scripts/uvicorn src.app:app --reload --port 8000
Giữ Retriever + OpenAI client dùng chung giữa các request (tải index 1 lần
lúc khởi động) thay vì tạo mới mỗi câu hỏi -- tránh gọi lại embedding corpus.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
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


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        _state["retriever"] = Retriever()
        _state["client"] = generation_client()
    except OpenAIError as e:
        # Lỗi phổ biến nhất khi mới cài đặt: thiếu/sai OPENAI_API_KEY trong
        # .env. Không bắt được lỗi này thì uvicorn chỉ in traceback sâu từ
        # bên trong thư viện openai, khó biết nguyên nhân thật.
        raise RuntimeError(
            "Không khởi động được server: lỗi cấu hình/kết nối OpenAI API. "
            "Kiểm tra OPENAI_API_KEY trong file .env (xem .env.example)."
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
def chat(req: ChatRequest) -> ChatResponse:
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
    return {"status": "ok", "chunks": len(_state["retriever"].chunks)}


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
