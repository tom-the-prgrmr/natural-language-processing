import json
from types import SimpleNamespace

from src.generation import REFUSAL_MESSAGE, answer

CHUNK = {
    "id": "168_D7_K8_b",
    "law": "168",
    "dieu": 7,
    "khoan": "8",
    "diem": "b",
    "name": "ND168",
    "effective_date": "2025-01-01",
    "status": "goc",
    "text": "Phạt tiền từ 6.000.000 đồng đến 8.000.000 đồng ...",
}


class FakeRetriever:
    def search(self, query, k):
        return [CHUNK]


class FakeClient:
    def __init__(self, content: str):
        msg = SimpleNamespace(content=content)
        resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
        create = lambda **kwargs: resp
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def _run(model_output: dict | str):
    content = (
        model_output if isinstance(model_output, str) else json.dumps(model_output)
    )
    return answer("q", retriever=FakeRetriever(), client=FakeClient(content))


def test_refused_uses_fixed_message_even_if_model_answer_is_garbage():
    r = _run({"answer": "{", "citations": [], "refused": True})
    assert r.refused
    assert r.answer == REFUSAL_MESSAGE


def test_refused_keeps_model_explanation_when_usable():
    msg = "Câu hỏi về lập trình Python nằm ngoài phạm vi tra cứu phạt giao thông."
    r = _run({"answer": msg, "citations": [], "refused": True})
    assert r.refused
    assert r.answer == msg


def test_known_foreign_word_is_replaced_not_discarded():
    msg = "Câu hỏi ngoài phạm vi. Bạn có thể hỏi, օրինակ: xe máy vượt đèn đỏ?"
    r = _run({"answer": msg, "citations": [], "refused": True})
    assert r.answer == msg.replace("օրինակ", "ví dụ")


def test_refusal_with_unknown_non_latin_word_falls_back():
    msg = "Câu hỏi ngoài phạm vi. Bạn có thể hỏi, пример: xe máy vượt đèn đỏ?"
    r = _run({"answer": msg, "citations": [], "refused": True})
    assert r.answer == REFUSAL_MESSAGE


def test_unparseable_output_is_refused_with_fixed_message():
    r = _run("not json")
    assert r.refused
    assert r.answer == REFUSAL_MESSAGE


def test_hallucinated_citation_forces_fixed_refusal_message():
    r = _run({"answer": "Phạt 1 tỷ", "citations": ["FAKE_ID"], "refused": False})
    assert r.refused
    assert r.hallucinated_citations == ["FAKE_ID"]
    assert r.answer == REFUSAL_MESSAGE


def test_refused_with_money_figure_in_answer_falls_back():
    # Lỗi đã biết (experiments/003): model đặt refused=True nhưng answer vẫn
    # chứa một số tiền cụ thể -- không đáng tin hơn trích dẫn bịa, phải thay
    # bằng câu dự phòng thay vì hiển thị mập mờ cho người dùng.
    msg = "Phạt tiền từ 6.000.000 đồng đến 8.000.000 đồng theo quy định."
    r = _run({"answer": msg, "citations": [], "refused": True})
    assert r.refused
    assert r.answer == REFUSAL_MESSAGE


def test_normal_answer_is_kept():
    r = _run(
        {"answer": "Phạt 6-8 triệu", "citations": ["168_D7_K8_b"], "refused": False}
    )
    assert not r.refused
    assert r.answer == "Phạt 6-8 triệu"


def test_citation_label_formats():
    from src.generation import citation_label

    assert (
        citation_label({"law": "168", "dieu": 7, "khoan": "8", "diem": "b", "name": ""})
        == "Điểm b, khoản 8, Điều 7 Nghị định 168/2024/NĐ-CP"
    )
    assert (
        citation_label(
            {"law": "L36", "dieu": 1, "khoan": "0", "diem": None, "name": ""}
        )
        == "Điều 1 Luật 36/2024/QH15"
    )
    assert citation_label(
        {
            "law": "238",
            "dieu": 2,
            "khoan": "1",
            "diem": None,
            "amends_dieu": 6,
            "name": "",
        }
    ) == ("Khoản 1, Điều 2 Nghị định 238/2026/NĐ-CP (sửa đổi Điều 6 NĐ 168)")


def test_answer_returns_citation_labels():
    r = _run(
        {"answer": "Phạt 6-8 triệu", "citations": ["168_D7_K8_b"], "refused": False}
    )
    assert r.citation_labels == ["Điểm b, khoản 8, Điều 7 Nghị định 168/2024/NĐ-CP"]


def test_amount_not_in_cited_chunk_forces_refusal():
    # Lỗi thật (experiments/006): model nói 4-6 triệu (từ trí nhớ riêng) nhưng
    # trích một chunk có thật trong ngữ cảnh mà chỉ ghi 6-8 triệu.
    r = _run(
        {
            "answer": "Phạt từ 4.000.000 đồng đến 6.000.000 đồng.",
            "citations": ["168_D7_K8_b"],
            "refused": False,
        }
    )
    assert r.refused
    assert r.ungrounded_amounts == ["4.000.000"]
    assert r.answer == REFUSAL_MESSAGE


def test_amount_grounded_in_cited_chunk_is_kept():
    msg = "Phạt từ 6.000.000 đồng đến 8.000.000 đồng. Căn cứ: điểm b khoản 8 Điều 7."
    r = _run({"answer": msg, "citations": ["168_D7_K8_b"], "refused": False})
    assert not r.refused
    assert r.ungrounded_amounts == []
    assert r.answer == msg


def test_amount_without_any_citation_forces_refusal():
    r = _run({"answer": "Phạt 6.000.000 đồng.", "citations": [], "refused": False})
    assert r.refused
    assert r.ungrounded_amounts == ["6.000.000"]


def test_amount_matching_is_by_token_not_substring():
    from src.generation import ungrounded_amounts

    # "8.000.000" là chuỗi con của "18.000.000" nhưng là mức phạt khác.
    chunks = [{"text": "Phạt tiền từ 18.000.000 đồng đến 20.000.000 đồng"}]
    assert ungrounded_amounts("Phạt 8.000.000 đồng.", chunks) == ["8.000.000"]
    assert ungrounded_amounts("Phạt 18.000.000 đồng.", chunks) == []


def test_derived_difference_of_grounded_amounts_is_accepted():
    from src.generation import ungrounded_amounts

    # Câu hỏi "ô tô phạt hơn xe máy bao nhiêu": 30tr - 8tr = 22tr là số suy ra
    # hợp lệ từ hai chunk được trích, không phải số bịa.
    chunks = [
        {"text": "Phạt tiền từ 30.000.000 đồng đến 40.000.000 đồng"},
        {"text": "Phạt tiền từ 8.000.000 đồng đến 10.000.000 đồng"},
    ]
    assert ungrounded_amounts("Ô tô cao hơn từ 22.000.000 đồng.", chunks) == []
    assert ungrounded_amounts("Ô tô cao hơn 25.000.000 đồng.", chunks) == ["25.000.000"]


def test_bracketed_citation_id_is_normalized():
    # Lỗi thật (experiments/007, q21): model chép cả ngoặc vuông của định dạng
    # ngữ cảnh "[id] ..." vào citations, id đúng bị coi là bịa.
    r = _run(
        {"answer": "Phạt 6-8 triệu", "citations": [" [168_D7_K8_b] "], "refused": False}
    )
    assert not r.refused
    assert r.citations == ["168_D7_K8_b"]
    assert r.hallucinated_citations == []
