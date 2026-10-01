from src.retrieval import expand_query


def test_expands_colloquial_terms_and_keeps_original_question():
    q = "Xe máy vượt đèn đỏ phạt bao nhiêu?"
    out = expand_query(q)
    assert out.startswith(q)
    assert "xe mô tô, xe gắn máy" in out
    assert "không chấp hành hiệu lệnh của đèn tín hiệu giao thông" in out


def test_question_already_in_legal_terms_is_unchanged():
    q = "Người lái ô tô không thắt dây an toàn bị phạt bao nhiêu?"
    assert expand_query(q) == q


def test_xe_dap_may_is_not_mistaken_for_xe_may():
    # Điều 9 (xe đạp, xe đạp máy) chính là điều khoản bị lấy nhầm ở experiments/006.
    assert "xe gắn máy" not in expand_query("Xe đạp máy vượt đèn đỏ phạt bao nhiêu?")


def test_each_legal_term_added_once():
    out = expand_query("nhậu xỉn say rượu bia lái xe hơi")
    assert out.count("nồng độ cồn") == 1
    assert "xe ô tô" in out
