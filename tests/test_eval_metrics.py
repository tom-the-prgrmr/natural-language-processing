"""Test eval/run_generation.py: numbers_covered() -- không gọi API, chỉ test
logic so khớp số thuần Python.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
from run_generation import numbers_covered


def test_money_match():
    assert numbers_covered(
        "Phạt tiền từ 400.000 đến 600.000 đồng (Điều 7 khoản 2 điểm h ND168).",
        "Xe máy bị phạt từ 400.000 đồng đến 600.000 đồng.",
    )


def test_money_missing_fails():
    assert not numbers_covered(
        "Phạt tiền từ 400.000 đến 600.000 đồng.",
        "Xe máy bị phạt từ 400.000 đồng đến 500.000 đồng.",  # sai số trên
    )


def test_speed_threshold_caught():
    gold = "Nếu vượt quá tốc độ quy định 25 km/h thì phạt 6.000.000 đến 8.000.000 đồng."
    assert numbers_covered(
        gold, "Phạt 6.000.000 đến 8.000.000 đồng, vượt quá tốc độ 25 km/h."
    )
    assert not numbers_covered(
        gold, "Phạt 6.000.000 đến 8.000.000 đồng."
    )  # thiếu 25 km/h


def test_point_deduction_caught():
    gold = "Phạt tiền 4.000.000-6.000.000 đồng và bị trừ 04 điểm giấy phép lái xe."
    assert numbers_covered(
        gold, "Phạt 4.000.000-6.000.000 đồng, trừ 4 điểm giấy phép lái xe."
    )
    assert not numbers_covered(gold, "Phạt 4.000.000-6.000.000 đồng.")  # thiếu điểm trừ


def test_citation_structure_is_not_mistaken_for_point_deduction():
    # Lỗi đã từng bắt được: "khoản 9 điểm b" không phải "9 điểm GPLX".
    gold = "Phạt tiền 18.000.000-20.000.000 đồng (Điều 6 khoản 9 điểm b ND168)."
    assert numbers_covered(
        gold,
        "Phạt từ 18.000.000 đồng đến 20.000.000 đồng. Căn cứ: điểm b khoản 9 Điều 6.",
    )


def test_meter_unit_word_spelled_out_is_accepted():
    # Bug thật phát hiện khi chạy lại: gold ghi "1,35 m", model viết "1,35
    # mét" (cùng nghĩa, khác cách viết) -- "m\\b" không khớp bên trong "mét".
    gold = "...chở trẻ em dưới 10 tuổi và cao dưới 1,35 m mà không dùng..."
    assert numbers_covered(gold, "Trẻ em dưới 10 tuổi và cao dưới 1,35 mét...")


def test_no_distinguishing_number_defaults_true():
    assert numbers_covered(
        "Bị tịch thu phương tiện (Điều 6 khoản 14 ND168).",
        "Xe bị tịch thu.",
    )
