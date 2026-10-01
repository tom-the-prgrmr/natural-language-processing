"""Sinh câu trả lời: retrieval top-k -> prompt ép trích dẫn -> JSON có cấu trúc.

Hỗ trợ hội thoại nhiều lượt tối thiểu (cắt phạm vi, xem docs/plan.md): không
tách bước "viết lại câu hỏi" riêng; câu truy vấn cho retrieval là ghép các lượt
hỏi trước đó + câu hỏi hiện tại (đơn giản, không hoàn hảo, nhưng đưa được từ
khoá ngữ cảnh — ví dụ "xe máy" nhắc ở lượt 1 — vào lượt 2 "còn ô tô thì sao?").
"""

import json
import re
import time
import unicodedata
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
15/08/2026). Giao diện đã hiển thị sẵn lưu ý "công cụ tham khảo, không phải tư \
vấn pháp lý", nên KHÔNG lặp lại câu này trong câu trả lời. Phần NGỮ CẢNH \
trong tin nhắn là do hệ thống tự tra cứu, người dùng không nhìn thấy: khi cần \
nhắc tới, gọi là "các quy định tôi tra được", KHÔNG nói "ngữ cảnh bạn cung cấp".

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên các đoạn văn bản (ngữ cảnh) được cung cấp dưới đây. \
KHÔNG được bịa số liệu, điều khoản, hay dùng kiến thức ngoài ngữ cảnh.
2. Nếu ngữ cảnh không đủ để trả lời chắc chắn (không có đoạn nào liên quan, \
hoặc câu hỏi ngoài phạm vi giao thông đường bộ Việt Nam), đặt "refused": true, \
KHÔNG đoán bừa, và trong "answer" viết 1-3 câu hoàn chỉnh, lịch sự: (a) nói rõ \
lý do — câu hỏi nằm ngoài phạm vi (nêu ngắn chủ đề câu hỏi) HOẶC thuộc phạm vi \
nhưng văn bản được cung cấp không có quy định phù hợp; (b) nhắc rằng bạn chỉ tra \
cứu mức phạt giao thông đường bộ theo các văn bản trên; (c) gợi ý 1 ví dụ câu \
hỏi phù hợp hoặc cách diễn đạt lại. Không để "answer" trống; "citations" là [].
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
6. Văn phong tự nhiên, như một người am hiểu luật giải thích cho người dân, \
HOÀN TOÀN bằng tiếng Việt (không chèn từ của ngôn ngữ khác), văn bản thuần \
(không markdown, không gạch đầu dòng), thường 2-4 câu:
   - Câu đầu trả lời thẳng câu hỏi (bị phạt bao nhiêu / có bị phạt không).
   - Diễn đạt bằng từ đời thường ("xe máy", "ô tô", "vượt đèn đỏ") thay vì \
chép nguyên câu chữ điều luật, NHƯNG giữ nguyên số tiền đúng như văn bản, \
viết đầy đủ dạng "từ X.000.000 đồng đến Y.000.000 đồng" (được thêm cách đọc \
gọn trong ngoặc, vd "(X–Y triệu)").
   - Chỉ nêu hình phạt bổ sung (trừ điểm, tước giấy phép lái xe...) khi có \
đoạn ngữ cảnh ghi RÕ con số cho đúng hành vi đó, và trích dẫn cả đoạn đó; \
không có thì bỏ qua, KHÔNG nói chung chung kiểu "bị trừ điểm theo quy định".
   - Câu cuối nêu căn cứ dạng "Căn cứ: điểm ... khoản ... Điều ... Nghị định \
168/2024/NĐ-CP." (ghi rõ văn bản/bản sửa đổi được áp dụng).
7. Lời chào, cảm ơn, hoặc hỏi bạn làm được gì: đáp lại thân thiện 1-2 câu, \
giới thiệu ngắn mình tra cứu mức phạt giao thông đường bộ; "refused": false, \
"citations": [].

Trả lời DUY NHẤT một object JSON đúng schema:
{"answer": "...", "citations": ["<id đoạn>", ...], "refused": bool, \
"needs_clarification": bool, "clarify_question": "..." hoặc null}

Ví dụ minh hoạ VĂN PHONG khi trả lời (X, Y, Z, ... là chỗ trống; số và điều \
khoản thật phải lấy từ ngữ cảnh, không lấy từ ví dụ này):
{"answer": "Xe máy [hành vi] sẽ bị phạt từ X.000.000 đồng đến Y.000.000 đồng \
(X–Y triệu). Ngoài ra, người vi phạm còn bị trừ Z điểm giấy phép lái xe. \
Căn cứ: điểm ... khoản ... Điều ... Nghị định 168/2024/NĐ-CP.", "citations": \
["<id đoạn>"], "refused": false, "needs_clarification": false, \
"clarify_question": null}

Ví dụ khi từ chối (câu hỏi "Đi máy bay mang bật lửa có bị phạt không?"):
{"answer": "Câu hỏi về quy định mang đồ lên máy bay nằm ngoài phạm vi của tôi. \
Tôi chỉ tra cứu mức phạt vi phạm giao thông đường bộ theo Luật 36/2024/QH15, \
ND 168/2024 và ND 238/2026. Bạn có thể hỏi, ví dụ: \\"Xe máy không đội mũ bảo \
hiểm bị phạt bao nhiêu?\\"", "citations": [], "refused": true, \
"needs_clarification": false, "clarify_question": null}
"""


# Câu từ chối dự phòng: chỉ dùng khi không dùng được lời từ chối model tự viết
# (rỗng/rác như "{", JSON lỗi) hoặc khi bị ép từ chối do trích dẫn bịa (text
# model viết lúc đó không đáng tin). Text gốc của model vẫn giữ trong raw.
REFUSAL_MESSAGE = (
    "Xin lỗi, tôi không có kiến thức cho câu hỏi này. Tôi chỉ tra cứu được mức "
    "phạt vi phạm giao thông đường bộ theo Luật 36/2024/QH15, Nghị định "
    "168/2024/NĐ-CP và Nghị định 238/2026/NĐ-CP."
)

# Lỗi lặp lại của gpt-5.4-mini: viết từ tiếng Armenia "օրինակ" (= "ví dụ") ở
# chỗ "Bạn có thể hỏi, ví dụ: ...". Sửa đúng từ đã biết thay vì bỏ cả câu.
KNOWN_FOREIGN_WORDS = {"օրինակ": "ví dụ"}

# Phát hiện cờ refused=True nhưng answer vẫn chứa một số tiền cụ thể (model tự
# mâu thuẫn -- xem experiments/003 "Lỗi còn thấy"): nếu vậy, answer đó trông
# như một câu trả lời thật nhưng lại bị gắn nhãn từ chối, không đáng tin hơn gì
# một trích dẫn bịa, nên cũng thay bằng câu dự phòng thay vì hiển thị mập mờ.
MONEY_RE = re.compile(r"\d{1,3}(?:\.\d{3})+\s*đồng")

# Số tiền dạng token đầy đủ ("18.000.000"), dùng để đối chiếu câu trả lời với
# nội dung chunk được trích. So theo token chứ không so chuỗi con: "8.000.000"
# là chuỗi con của "18.000.000" nhưng là một mức phạt khác.
AMOUNT_RE = re.compile(r"\d{1,3}(?:\.\d{3})+")


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
    ungrounded_amounts: list[str] = field(default_factory=list)
    citation_labels: list[str] = field(default_factory=list)
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


LAW_SHORT_NAMES = {
    "L36": "Luật 36/2024/QH15",
    "168": "Nghị định 168/2024/NĐ-CP",
    "238": "Nghị định 238/2026/NĐ-CP",
}


def citation_label(chunk: dict) -> str:
    """ID chunk -> nhãn dễ đọc, vd 168_D7_K8_b -> "Điểm b, khoản 8, Điều 7
    Nghị định 168/2024/NĐ-CP". Khoản "0" là cả điều (không có khoản)."""
    parts = []
    if chunk.get("diem"):
        parts.append(f"điểm {chunk['diem']}")
    if chunk.get("khoan") not in (None, "0"):
        parts.append(f"khoản {chunk['khoan']}")
    parts.append(f"Điều {chunk['dieu']}")
    label = ", ".join(parts)
    label = label[0].upper() + label[1:]
    law = LAW_SHORT_NAMES.get(chunk["law"], chunk["name"])
    label = f"{label} {law}"
    if chunk.get("amends_dieu"):
        label += f" (sửa đổi Điều {chunk['amends_dieu']} NĐ 168)"
    return label


def _is_usable_text(text: str) -> bool:
    """Lọc lời từ chối rác: quá ngắn/không có chữ (vd. "{", "refused"), hoặc lẫn
    chữ ngoài bảng Latin (model đôi khi chèn từ tiếng Armenia "օրինակ"; chữ
    tiếng Việt có dấu đều thuộc Latin)."""
    letters = [ch for ch in text if ch.isalpha()]
    return (
        len(text) >= 15
        and bool(letters)
        and all(unicodedata.name(ch, "").startswith("LATIN") for ch in letters)
    )


def _amount_value(token: str) -> int:
    return int(token.replace(".", ""))


def ungrounded_amounts(text: str, cited_chunks: list[dict]) -> list[str]:
    """Số tiền nêu trong câu trả lời nhưng không có trong nội dung chunk nào
    được trích dẫn -- tức model lấy số từ chỗ khác (thường là trí nhớ riêng)
    rồi gắn một trích dẫn có thật nhưng không chứa số đó.

    Chấp nhận số suy ra bằng hiệu/tổng của hai số có căn cứ (câu hỏi kiểu "ô
    tô phạt hơn xe máy bao nhiêu": 30.000.000 - 8.000.000 = 22.000.000)."""
    grounded = {
        _amount_value(a) for c in cited_chunks for a in AMOUNT_RE.findall(c["text"])
    }
    derived = {abs(x - y) for x in grounded for y in grounded} | {
        x + y for x in grounded for y in grounded
    }
    return [
        a
        for a in dict.fromkeys(AMOUNT_RE.findall(text))
        if _amount_value(a) not in grounded and _amount_value(a) not in derived
    ]


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
    by_id = {c["id"]: c for c in chunks}
    # Ngữ cảnh ghi id dạng "[168_D6_K11_a] ..." nên model đôi khi chép luôn
    # ngoặc vuông vào citations -- không chuẩn hoá thì id đúng bị coi là bịa.
    citations = [
        str(c).strip().strip("[]").strip() for c in data.get("citations") or []
    ]
    refused = bool(data.get("refused", False))

    # "Tự nghĩ thêm": kiểm tra trích dẫn tự động -- id model trích dẫn phải
    # thực sự nằm trong các chunk đã truy xuất (không được bịa id). Nếu có
    # trích dẫn bịa, coi câu trả lời KHÔNG đáng tin và ép refused=True thay vì
    # để người dùng tin một câu trả lời có vẻ có căn cứ nhưng thực ra không.
    hallucinated = [c for c in citations if c not in retrieved_ids]
    if hallucinated:
        refused = True

    text = str(data.get("answer") or "").strip()
    for foreign, vi in KNOWN_FOREIGN_WORDS.items():
        text = text.replace(foreign, vi)

    # Mức thứ hai của kiểm tra trích dẫn: id hợp lệ chưa đủ, mọi số tiền trong
    # câu trả lời còn phải có trong nội dung các chunk được trích. Bắt trường
    # hợp model trả lời bằng trí nhớ riêng rồi gắn một id có trong ngữ cảnh
    # nhưng không liên quan (xem experiments/006).
    ungrounded: list[str] = []
    if not refused:
        ungrounded = ungrounded_amounts(
            text, [by_id[c] for c in citations if c in by_id]
        )
        if ungrounded:
            refused = True

    if refused and (
        hallucinated or ungrounded or not _is_usable_text(text) or MONEY_RE.search(text)
    ):
        text = REFUSAL_MESSAGE

    return AnswerResult(
        answer=text,
        citations=citations,
        refused=refused,
        needs_clarification=bool(data.get("needs_clarification", False)),
        clarify_question=data.get("clarify_question"),
        retrieved_ids=retrieved_ids,
        hallucinated_citations=hallucinated,
        ungrounded_amounts=ungrounded,
        citation_labels=[citation_label(by_id[c]) for c in citations if c in by_id],
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
