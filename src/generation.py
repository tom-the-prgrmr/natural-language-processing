"""Sinh câu trả lời: retrieval top-k -> prompt ép trích dẫn -> JSON có cấu trúc.

Hỗ trợ hội thoại nhiều lượt tối thiểu (cắt phạm vi, xem docs/plan.md): không
tách bước "viết lại câu hỏi" riêng; câu truy vấn cho retrieval là ghép các lượt
hỏi trước đó + câu hỏi hiện tại (đơn giản, không hoàn hảo, nhưng đưa được từ
khoá ngữ cảnh — ví dụ "xe máy" nhắc ở lượt 1 — vào lượt 2 "còn ô tô thì sao?").
"""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from dotenv import load_dotenv
from openai import OpenAI

from src.retrieval import Retriever

GEN_MODEL = "gpt-5.4-mini"
TOP_K = 12  # chốt sau ablation k=8 vs k=12 trên dev, xem experiments/002

SYSTEM_PROMPT_TEMPLATE = """\
Bạn là trợ lý tra cứu mức phạt vi phạm giao thông đường bộ Việt Nam, dựa trên \
Luật Trật tự an toàn giao thông đường bộ 36/2024/QH15, Nghị định 168/2024/NĐ-CP \
và Nghị định 238/2026/NĐ-CP (sửa đổi một số điều của ND168, hiệu lực từ \
15/08/2026). Đây là CÔNG CỤ THAM KHẢO, KHÔNG PHẢI TƯ VẤN PHÁP LÝ — luôn nói rõ \
điều này khi phù hợp.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên các đoạn văn bản (ngữ cảnh) được cung cấp dưới đây. \
KHÔNG được bịa số liệu, điều khoản, hay dùng kiến thức ngoài ngữ cảnh.
2. Nếu ngữ cảnh không đủ để trả lời chắc chắn (không có đoạn nào liên quan, \
hoặc câu hỏi ngoài phạm vi giao thông đường bộ Việt Nam), đặt "refused": true \
và giải thích ngắn gọn, KHÔNG đoán bừa.
3. Nếu câu hỏi thiếu thông tin cần thiết để xác định đúng mức phạt (thường là \
LOẠI XE: ô tô hay xe máy — vì hai loại phạt khác nhau rất nhiều), đặt \
"needs_clarification": true và hỏi lại trong "clarify_question" thay vì đoán.
4. Nếu có nhiều đoạn liên quan tới cùng một hành vi nhưng KHÁC ngày hiệu lực \
(ví dụ bản gốc ND168 và bản sửa đổi ND238), chọn đoạn có "status": "sua_doi" \
NẾU hành vi xảy ra từ "effective_date" của đoạn đó trở đi; nếu hành vi xảy ra \
trước đó, dùng đoạn "status": "goc". Nếu câu hỏi không nói rõ thời điểm, mặc \
định coi là thời điểm hiện tại ({today}) và ưu tiên quy định mới nhất đã có \
hiệu lực.
5. Mọi mức phạt nêu ra phải kèm trích dẫn (id đoạn văn bản dùng) trong \
"citations". Không trích dẫn đoạn không thực sự dùng để suy ra câu trả lời.
6. Trả lời ngắn gọn, đúng trọng tâm, tiếng Việt.

Trả lời DUY NHẤT một object JSON đúng schema:
{"answer": "...", "citations": ["<id đoạn>", ...], "refused": bool, \
"needs_clarification": bool, "clarify_question": "..." hoặc null}
"""


@dataclass
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class AnswerResult:
    answer: str
    citations: list[str]
    refused: bool
    needs_clarification: bool
    clarify_question: str | None
    retrieved_ids: list[str] = field(default_factory=list)
    hallucinated_citations: list[str] = field(default_factory=list)
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    raw: dict = field(default_factory=dict)


def _client() -> OpenAI:
    load_dotenv()
    return OpenAI()


def _system_prompt(as_of: date | None = None) -> str:
    """Chèn ngày hiện tại (mặc định: ngày chạy thật) vào prompt, không gõ chết
    một ngày cụ thể — ngày hiệu lực luật thay đổi theo thời gian thật."""
    today = (as_of or datetime.now(UTC).date()).isoformat()
    return SYSTEM_PROMPT_TEMPLATE.replace("{today}", today)


def _retrieval_query(history: list[Turn], question: str) -> str:
    user_turns = [t.content for t in history if t.role == "user"]
    return " ".join([*user_turns, question])


def _format_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f"[{c['id']}] (văn bản: {c['name']}, hiệu lực: {c['effective_date']}, "
            f"trạng thái: {c['status']})\n{c['text']}"
        )
    return "\n\n".join(parts)


def answer(
    question: str,
    history: list[Turn] | None = None,
    retriever: Retriever | None = None,
    client: OpenAI | None = None,
    k: int = TOP_K,
    model: str = GEN_MODEL,
    as_of: date | None = None,
) -> AnswerResult:
    """as_of: ngày coi là "hiện tại" khi câu hỏi không tự nêu thời điểm (mặc
    định: ngày chạy thật). Cố định giá trị này khi cần kết quả tái lập được."""
    history = history or []
    retriever = retriever or Retriever()
    client = client or _client()

    t0 = time.perf_counter()
    query = _retrieval_query(history, question)
    chunks = retriever.search(query, k=k)
    retrieval_ms = (time.perf_counter() - t0) * 1000

    messages = [{"role": "system", "content": _system_prompt(as_of)}]
    for t in history:
        messages.append({"role": t.role, "content": t.content})
    messages.append(
        {
            "role": "user",
            "content": f"NGỮ CẢNH:\n{_format_context(chunks)}\n\nCÂU HỎI: {question}",
        }
    )

    t1 = time.perf_counter()
    resp = client.chat.completions.create(
        model=model, messages=messages, response_format={"type": "json_object"}
    )
    generation_ms = (time.perf_counter() - t1) * 1000

    raw_text = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        data = {
            "answer": "",
            "citations": [],
            "refused": True,
            "needs_clarification": False,
            "clarify_question": None,
            "_parse_error": raw_text,
        }

    retrieved_ids = [c["id"] for c in chunks]
    citations = data.get("citations", []) or []
    refused = bool(data.get("refused", False))

    # "Tự nghĩ thêm": kiểm tra trích dẫn tự động -- id model trích dẫn phải
    # thực sự nằm trong các chunk đã truy xuất (không được bịa id). Nếu có
    # trích dẫn bịa, coi câu trả lời KHÔNG đáng tin và ép refused=True thay vì
    # để người dùng tin một câu trả lời có vẻ có căn cứ nhưng thực ra không.
    hallucinated = [c for c in citations if c not in retrieved_ids]
    if hallucinated:
        refused = True

    return AnswerResult(
        answer=data.get("answer", ""),
        citations=citations,
        refused=refused,
        needs_clarification=bool(data.get("needs_clarification", False)),
        clarify_question=data.get("clarify_question"),
        retrieved_ids=retrieved_ids,
        hallucinated_citations=hallucinated,
        retrieval_ms=retrieval_ms,
        generation_ms=generation_ms,
        raw=data,
    )


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    q = sys.argv[1] if len(sys.argv) > 1 else "Xe máy vượt đèn đỏ phạt bao nhiêu?"
    r = answer(q)
    print(f"Retrieved: {r.retrieved_ids}")
    print(f"Retrieval: {r.retrieval_ms:.0f}ms  Generation: {r.generation_ms:.0f}ms")
    print(json.dumps(r.raw, ensure_ascii=False, indent=2))
