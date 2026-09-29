"""Sinh data/eval/dev.jsonl + test.jsonl (bản nháp 40 câu, xem docs/plan.md).

Soạn bởi Claude 2026-09-29, tra trực tiếp từ data/processed/chunks.jsonl (đã
đối chiếu với data/raw/ ở bước ingest). Đây là NHÁP — theo docs/plan.md, do cắt
phạm vi 2 ngày, người dùng duyệt nhanh thay vì tự viết tay toàn bộ. Chạy một lần
để tạo file, không chạy lại tự động (script này không nằm trong pipeline).
"""

import json
from pathlib import Path

AS_OF = "2026-09-29"
SRC = "llm_draft_reviewed"
VERIFIED_BY = (
    "Claude, tra trực tiếp data/processed/chunks.jsonl 2026-09-29 -- "
    "CHƯA được người dùng duyệt (cắt phạm vi do gấp hạn, xem docs/plan.md)"
)

# (id, split, group, vehicle, question, gold_chunks, gold_answer, answerable)
ITEMS = [
    # --- muc_phat_truc_tiep (12: dev 5 / test 7) ---
    (
        "q01",
        "dev",
        "muc_phat_truc_tiep",
        "xe_may",
        "Xe máy không đội mũ bảo hiểm bị phạt bao nhiêu?",
        ["168_D7_K2_h"],
        "Phạt tiền từ 400.000 đến 600.000 đồng (Điều 7 khoản 2 điểm h ND168).",
        True,
    ),
    (
        "q02",
        "dev",
        "muc_phat_truc_tiep",
        "xe_may",
        "Xe máy chở 2 người ngồi sau (không phải cấp cứu, trẻ em, người già yếu...) phạt thế nào?",
        ["168_D7_K2_g"],
        "Phạt tiền từ 400.000 đến 600.000 đồng (Điều 7 khoản 2 điểm g ND168).",
        True,
    ),
    (
        "q03",
        "dev",
        "muc_phat_truc_tiep",
        "o_to",
        "Người lái ô tô không thắt dây an toàn khi xe đang chạy bị phạt bao nhiêu?",
        ["168_D6_K3_k"],
        "Phạt tiền từ 800.000 đến 1.000.000 đồng (Điều 6 khoản 3 điểm k ND168).",
        True,
    ),
    (
        "q04",
        "dev",
        "muc_phat_truc_tiep",
        "o_to",
        "Hành khách ngồi trên ô tô ở vị trí có dây an toàn mà không thắt thì ai bị phạt và bao nhiêu?",
        ["168_D6_K3_l"],
        "Người điều khiển xe bị phạt 800.000 đến 1.000.000 đồng vì để người trên xe không thắt dây an toàn tại vị trí có trang bị (Điều 6 khoản 3 điểm l ND168).",
        True,
    ),
    (
        "q05",
        "dev",
        "muc_phat_truc_tiep",
        "xe_may",
        "Đang lái xe máy mà cầm điện thoại nghe gọi thì phạt bao nhiêu?",
        ["168_D7_K4_đ"],
        "Phạt tiền từ 800.000 đến 1.000.000 đồng (Điều 7 khoản 4 điểm đ ND168).",
        True,
    ),
    (
        "q06",
        "test",
        "muc_phat_truc_tiep",
        "o_to",
        'Ô tô đỗ ở nơi có biển "Cấm đỗ xe" bị phạt bao nhiêu?',
        ["168_D6_K3_e"],
        "Phạt tiền từ 800.000 đến 1.000.000 đồng (Điều 6 khoản 3 điểm e ND168).",
        True,
    ),
    (
        "q07",
        "test",
        "muc_phat_truc_tiep",
        "o_to",
        "Lái ô tô mà trong hơi thở có nồng độ cồn ở mức thấp nhất (chưa vượt 0,25 mg/lít khí thở) thì phạt bao nhiêu?",
        ["168_D6_K6_c"],
        "Phạt tiền từ 6.000.000 đến 8.000.000 đồng (Điều 6 khoản 6 điểm c ND168).",
        True,
    ),
    (
        "q08",
        "test",
        "muc_phat_truc_tiep",
        "xe_may",
        "Xe máy có nồng độ cồn ở mức thấp nhất (chưa vượt 0,25 mg/lít khí thở) phạt bao nhiêu?",
        ["168_D7_K6_a"],
        "Phạt tiền từ 2.000.000 đến 3.000.000 đồng (Điều 7 khoản 6 điểm a ND168).",
        True,
    ),
    (
        "q09",
        "test",
        "muc_phat_truc_tiep",
        "xe_may",
        "Xe máy chạy quá tốc độ trên 20 km/h thì phạt bao nhiêu?",
        ["168_D7_K8_a"],
        "Phạt tiền từ 6.000.000 đến 8.000.000 đồng (Điều 7 khoản 8 điểm a ND168).",
        True,
    ),
    (
        "q10",
        "test",
        "muc_phat_truc_tiep",
        "o_to",
        "Ô tô chạy quá tốc độ từ 20 đến 35 km/h phạt bao nhiêu?",
        ["168_D6_K6_a"],
        "Phạt tiền từ 6.000.000 đến 8.000.000 đồng (Điều 6 khoản 6 điểm a ND168).",
        True,
    ),
    (
        "q11",
        "test",
        "muc_phat_truc_tiep",
        "o_to",
        "Ô tô không chấp hành hiệu lệnh đèn tín hiệu giao thông (vượt đèn đỏ) phạt bao nhiêu?",
        ["168_D6_K9_b"],
        "Phạt tiền từ 18.000.000 đến 20.000.000 đồng (Điều 6 khoản 9 điểm b ND168).",
        True,
    ),
    (
        "q12",
        "test",
        "muc_phat_truc_tiep",
        "xe_may",
        "Xe máy vượt đèn đỏ (không chấp hành hiệu lệnh đèn tín hiệu) bị phạt bao nhiêu?",
        ["168_D7_K7_c"],
        "Phạt tiền từ 4.000.000 đến 6.000.000 đồng (Điều 7 khoản 7 điểm c ND168).",
        True,
    ),
    # --- doi_thuong (8: dev 3 / test 5), văn nói ---
    (
        "q13",
        "dev",
        "doi_thuong",
        "o_to",
        "xài điện thoại lúc lái ô tô bị phạt nhiêu vậy",
        ["168_D6_K5_h"],
        "Phạt tiền từ 4.000.000 đến 6.000.000 đồng (Điều 6 khoản 5 điểm h ND168).",
        True,
    ),
    (
        "q14",
        "dev",
        "doi_thuong",
        "o_to",
        "say rượu lái xe hơi ở mức nặng nhất thì phạt sao",
        ["168_D6_K11_a"],
        "Phạt tiền từ 30.000.000 đến 40.000.000 đồng đối với nồng độ cồn vượt quá 80 miligam/100 mililít máu hoặc vượt quá 0,4 miligam/lít khí thở (Điều 6 khoản 11 điểm a ND168).",
        True,
    ),
    (
        "q15",
        "dev",
        "doi_thuong",
        "xe_may",
        "nhậu xỉn chạy xe máy mức nặng nhất bị gì",
        ["168_D7_K9_d"],
        "Phạt tiền từ 8.000.000 đến 10.000.000 đồng đối với nồng độ cồn vượt quá 80 miligam/100 mililít máu hoặc vượt quá 0,4 miligam/lít khí thở (Điều 7 khoản 9 điểm d ND168).",
        True,
    ),
    (
        "q16",
        "test",
        "doi_thuong",
        "o_to",
        "lạng lách xe hơi lần 2 (tái phạm) bị sao không",
        ["168_D6_K14"],
        "Bị tịch thu phương tiện (Điều 6 khoản 14 ND168, áp dụng khi tái phạm hành vi lạng lách, đánh võng ở khoản 12).",
        True,
    ),
    (
        "q17",
        "test",
        "doi_thuong",
        "xe_may",
        "bốc đầu lạng lách xe máy mà tái phạm thì bị gì",
        ["168_D7_K11_c"],
        "Bị tịch thu phương tiện (Điều 7 khoản 11 điểm c ND168, áp dụng khi tái phạm hành vi lạng lách, đánh võng ở điểm a khoản 9).",
        True,
    ),
    (
        "q18",
        "test",
        "doi_thuong",
        "o_to",
        "chở con nít ngồi ghế trước xe hơi mà không có ghế an toàn giờ phạt chưa",
        ["238_D2_1"],
        "Có: phạt cảnh cáo đối với hành vi chở trẻ em dưới 10 tuổi và cao dưới 1,35 m mà không dùng thiết bị an toàn phù hợp (khoản 1a Điều 6 ND168, do Điều 2 ND238 bổ sung). Quy định này có hiệu lực từ 15/08/2026.",
        True,
    ),
    (
        "q19",
        "test",
        "doi_thuong",
        "xe_may",
        "xe máy nẹt pô rú ga liên tục trong khu dân cư phạt nhiêu",
        ["168_D7_K9_k"],
        "Phạt tiền từ 8.000.000 đến 10.000.000 đồng (Điều 7 khoản 9 điểm k ND168).",
        True,
    ),
    (
        "q20",
        "test",
        "doi_thuong",
        "o_to",
        "ô tô chạy 25km/h vượt quá tốc độ cho phép thì phạt nhiêu",
        ["168_D6_K6_a"],
        "Nếu vượt quá tốc độ quy định 25 km/h (nằm trong khoảng 20-35 km/h) thì phạt 6.000.000 đến 8.000.000 đồng (Điều 6 khoản 6 điểm a ND168).",
        True,
    ),
    # --- nhieu_dieu_kien (6: dev 2 / test 4), phạt tiền + hình phạt bổ sung ---
    (
        "q21",
        "dev",
        "nhieu_dieu_kien",
        "o_to",
        "Lái ô tô nồng độ cồn vượt quá 80 miligam/100ml máu thì ngoài phạt tiền còn bị gì nữa không?",
        ["168_D6_K11_a", "168_D6_K15_c"],
        "Phạt tiền 30.000.000-40.000.000 đồng (Điều 6 khoản 11 điểm a) và bị tước quyền sử dụng giấy phép lái xe từ 22 đến 24 tháng (Điều 6 khoản 15 điểm c ND168).",
        True,
    ),
    (
        "q22",
        "dev",
        "nhieu_dieu_kien",
        "xe_may",
        "Xe máy nồng độ cồn vượt quá 80 miligam/100ml máu bị phạt và tước bằng bao lâu?",
        ["168_D7_K9_d", "168_D7_K12_c"],
        "Phạt tiền 8.000.000-10.000.000 đồng (Điều 7 khoản 9 điểm d) và bị tước quyền sử dụng giấy phép lái xe từ 22 đến 24 tháng (Điều 7 khoản 12 điểm c ND168).",
        True,
    ),
    (
        "q23",
        "test",
        "nhieu_dieu_kien",
        "o_to",
        "Ô tô dùng điện thoại khi lái xe thì phạt tiền và bị trừ mấy điểm bằng lái?",
        ["168_D6_K5_h", "168_D6_K16_b"],
        "Phạt tiền 4.000.000-6.000.000 đồng (Điều 6 khoản 5 điểm h) và bị trừ 04 điểm giấy phép lái xe (Điều 6 khoản 16 điểm b ND168).",
        True,
    ),
    (
        "q24",
        "test",
        "nhieu_dieu_kien",
        "xe_may",
        "Xe máy nồng độ cồn ở mức 50-80 miligam/100ml máu thì phạt tiền và trừ bao nhiêu điểm bằng lái?",
        ["168_D7_K8_b", "168_D7_K13_d"],
        "Phạt tiền 6.000.000-8.000.000 đồng (Điều 7 khoản 8 điểm b) và bị trừ 10 điểm giấy phép lái xe (Điều 7 khoản 13 điểm d ND168).",
        True,
    ),
    (
        "q25",
        "test",
        "nhieu_dieu_kien",
        "o_to",
        "Ô tô lạng lách đánh võng, nếu tái phạm thì ngoài phạt tiền lần đầu còn bị xử lý thêm thế nào?",
        ["168_D6_K12", "168_D6_K14"],
        "Lần đầu: phạt tiền 40.000.000-50.000.000 đồng (Điều 6 khoản 12). Nếu tái phạm: bị tịch thu phương tiện (Điều 6 khoản 14 ND168).",
        True,
    ),
    (
        "q26",
        "test",
        "nhieu_dieu_kien",
        "xe_may",
        "Xe máy lạng lách đánh võng lần đầu và tái phạm thì bị xử lý khác nhau thế nào?",
        ["168_D7_K9_a", "168_D7_K11_c"],
        "Lần đầu: phạt tiền 8.000.000-10.000.000 đồng (Điều 7 khoản 9 điểm a). Nếu tái phạm: bị tịch thu phương tiện (Điều 7 khoản 11 điểm c ND168).",
        True,
    ),
    # --- phu_thuoc_loai_xe (6: dev 2 / test 4), so sánh ô tô vs xe máy ---
    (
        "q27",
        "dev",
        "phu_thuoc_loai_xe",
        None,
        "Vượt đèn đỏ thì ô tô và xe máy phạt khác nhau thế nào?",
        ["168_D6_K9_b", "168_D7_K7_c"],
        "Ô tô: 18.000.000-20.000.000 đồng (Điều 6 khoản 9 điểm b). Xe máy: 4.000.000-6.000.000 đồng (Điều 7 khoản 7 điểm c ND168).",
        True,
    ),
    (
        "q28",
        "dev",
        "phu_thuoc_loai_xe",
        None,
        "Dùng điện thoại khi lái xe, ô tô với xe máy phạt như nhau không?",
        ["168_D6_K5_h", "168_D7_K4_đ"],
        "Không giống nhau. Ô tô: 4.000.000-6.000.000 đồng (Điều 6 khoản 5 điểm h). Xe máy: 800.000-1.000.000 đồng (Điều 7 khoản 4 điểm đ ND168).",
        True,
    ),
    (
        "q29",
        "test",
        "phu_thuoc_loai_xe",
        None,
        "Chạy quá tốc độ trên 20 km/h, ô tô và xe máy phạt mức nào?",
        ["168_D6_K6_a", "168_D7_K8_a"],
        "Cùng khung 6.000.000-8.000.000 đồng: ô tô cho mức vượt 20-35 km/h (Điều 6 khoản 6 điểm a), xe máy cho mức vượt trên 20 km/h (Điều 7 khoản 8 điểm a ND168).",
        True,
    ),
    (
        "q30",
        "test",
        "phu_thuoc_loai_xe",
        None,
        "Nồng độ cồn ở mức thấp nhất, ô tô phạt nặng hơn xe máy đúng không?",
        ["168_D6_K6_c", "168_D7_K6_a"],
        "Đúng. Ô tô: 6.000.000-8.000.000 đồng (Điều 6 khoản 6 điểm c). Xe máy: 2.000.000-3.000.000 đồng (Điều 7 khoản 6 điểm a ND168).",
        True,
    ),
    (
        "q31",
        "test",
        "phu_thuoc_loai_xe",
        None,
        "Nồng độ cồn mức cao nhất (trên 80 miligam/100ml máu), tiền phạt ô tô chênh lệch bao nhiêu so với xe máy?",
        ["168_D6_K11_a", "168_D7_K9_d"],
        "Ô tô: 30.000.000-40.000.000 đồng (Điều 6 khoản 11 điểm a). Xe máy: 8.000.000-10.000.000 đồng (Điều 7 khoản 9 điểm d ND168). Mức ô tô cao hơn nhiều.",
        True,
    ),
    (
        "q32",
        "test",
        "phu_thuoc_loai_xe",
        None,
        "Lạng lách đánh võng lần đầu, ô tô hay xe máy bị phạt tiền nhiều hơn?",
        ["168_D6_K12", "168_D7_K9_a"],
        "Ô tô cao hơn: 40.000.000-50.000.000 đồng (Điều 6 khoản 12) so với xe máy 8.000.000-10.000.000 đồng (Điều 7 khoản 9 điểm a ND168).",
        True,
    ),
    # --- ngoai_pham_vi (4: dev 2 / test 2) ---
    (
        "q33",
        "dev",
        "ngoai_pham_vi",
        None,
        "Thủ tục đăng ký kết hôn cần giấy tờ gì?",
        [],
        "Ngoài phạm vi văn bản về xử phạt giao thông đường bộ mà hệ thống có; nên từ chối trả lời.",
        False,
    ),
    (
        "q34",
        "dev",
        "ngoai_pham_vi",
        None,
        "Thuế thu nhập cá nhân năm nay tính như thế nào?",
        [],
        "Ngoài phạm vi; nên từ chối trả lời.",
        False,
    ),
    (
        "q35",
        "test",
        "ngoai_pham_vi",
        None,
        "Cách nấu phở bò truyền thống thế nào?",
        [],
        "Ngoài phạm vi; nên từ chối trả lời.",
        False,
    ),
    (
        "q36",
        "test",
        "ngoai_pham_vi",
        None,
        "Luật đất đai quy định thế nào về cấp sổ đỏ?",
        [],
        "Ngoài phạm vi; nên từ chối trả lời.",
        False,
    ),
    # --- bay_loi_thoi (4: dev 2 / test 2) ---
    (
        "q37",
        "dev",
        "bay_loi_thoi",
        "xe_may",
        "Theo Nghị định 100/2019, xe máy vượt đèn đỏ phạt bao nhiêu?",
        [],
        "Hệ thống không có Nghị định 100/2019 trong corpus (đã bị ND168/2024 thay thế phần xử phạt đường bộ từ 01/01/2025); nên nói rõ không có dữ liệu về văn bản này thay vì bịa số, và nêu mức hiện hành theo ND168 nếu người dùng cần (Điều 7 khoản 7 điểm c: 4.000.000-6.000.000 đồng).",
        False,
    ),
    (
        "q38",
        "dev",
        "bay_loi_thoi",
        "o_to",
        "Ngày 01/08/2026, tôi chở con 8 tuổi ngồi ghế trước ô tô không dùng thiết bị an toàn. Lúc đó có bị phạt theo lỗi này không?",
        ["238_D2_1"],
        "Không bị phạt theo khoản 1a Điều 6 ND168 (do ND238 bổ sung), vì quy định này chỉ có hiệu lực từ 15/08/2026 — hành vi ngày 01/08/2026 xảy ra trước mốc đó.",
        True,
    ),
    (
        "q39",
        "test",
        "bay_loi_thoi",
        "o_to",
        "Nghe nói giờ ô tô vượt đèn đỏ bị phạt kịch khung tới 40 triệu luôn, có đúng không?",
        ["168_D6_K9_b"],
        "Không đúng. Mức phạt vượt đèn đỏ với ô tô là 18.000.000-20.000.000 đồng (Điều 6 khoản 9 điểm b ND168), không phải 40 triệu.",
        True,
    ),
    (
        "q40",
        "test",
        "bay_loi_thoi",
        None,
        "Thiết bị ghi hình khoang chở khách bắt buộc lắp ngay khi ND238 có hiệu lực 15/08/2026, đúng không?",
        ["238_D18_4"],
        "Không đúng. Riêng quy định xử phạt về thiết bị ghi nhận hình ảnh khoang chở khách (điểm n khoản 5 Điều 20; điểm k, l khoản 7 Điều 26 ND168) có hiệu lực thi hành riêng từ 01/01/2029, không phải từ 15/08/2026.",
        True,
    ),
]


def build(split: str) -> list[dict]:
    out = []
    for (
        id_,
        sp,
        group,
        vehicle,
        question,
        gold_chunks,
        gold_answer,
        answerable,
    ) in ITEMS:
        if sp != split:
            continue
        out.append(
            {
                "id": id_,
                "split": split,
                "question": question,
                "group": group,
                "vehicle": vehicle,
                "gold_chunks": gold_chunks,
                "gold_answer": gold_answer,
                "answerable": answerable,
                "as_of": AS_OF,
                "source": SRC,
                "verified_by": VERIFIED_BY,
            }
        )
    return out


def main() -> None:
    out_dir = Path(__file__).parent
    for split in ("dev", "test"):
        items = build(split)
        path = out_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"{split}: {len(items)} câu -> {path}")


if __name__ == "__main__":
    main()
