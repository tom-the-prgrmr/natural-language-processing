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
