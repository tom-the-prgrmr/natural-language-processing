# Tập đánh giá: schema và quy tắc

Mỗi dòng của `data/eval/dev.jsonl` / `test.jsonl` là một JSON:

```json
{
  "id": "q017",
  "split": "dev",
  "question": "vượt đèn đỏ xe máy bị phạt bao nhiêu",
  "group": "muc_phat_truc_tiep",
  "vehicle": "xe_may",
  "gold_chunks": ["168_D7_K4"],
  "gold_answer": "Từ 800.000 đến 1.000.000 đồng; trừ 4 điểm GPLX",
  "answerable": true,
  "as_of": "2026-09-20",
  "source": "manual",
  "verified_by": "tên người tra và ngày"
}
```

## Nhóm (`group`) và tỉ trọng mục tiêu (~100 câu)
`muc_phat_truc_tiep` (~30), `doi_thuong` (~20, văn nói, sai chính tả, viết tắt), `phu_thuoc_loai_xe` (~15), `nhieu_dieu_kien` (~15, hình phạt bổ sung: tước bằng, trừ điểm), `ngoai_pham_vi` (~10, `answerable=false`, `gold_chunks=[]`), `bay_loi_thoi` (~10, luật cũ hoặc tiền đề sai, ví dụ ND100/2019 hoặc hành vi trước/sau 15/08/2026).

## Nhóm hội thoại nhiều lượt (`nhieu_luot`, ~10 hội thoại)
Dùng cho chatbot. Mỗi mục có thêm trường `history` (các lượt trước: `[{"role":"user","content":...},{"role":"assistant","content":...}]`), còn `question` là lượt cuối, thường phụ thuộc ngữ cảnh ("còn ô tô thì sao?", "vậy bị trừ mấy điểm?"). `gold_chunks`/`gold_answer` chấm cho lượt cuối. Riêng câu thiếu thông tin (không nói loại xe) đặt `expect_clarify: true`: hệ thống phải hỏi lại thay vì đoán. Chấm và báo cáo tách riêng khỏi các nhóm còn lại.

## Quy tắc gán nhãn
- `gold_chunks` dùng ID ở **mức khoản** (`168_D7_K4`); nếu chunk tách theo điểm thì thêm hậu tố điểm. Việc so khớp retrieval tính đúng khi ID truy xuất bắt đầu bằng ID khoản vàng.
- `gold_answer` **tự tra từ `data/raw/` và tự đọc**. Ghi khoảng phạt đủ hai đầu, điểm bị trừ, hình phạt bổ sung nếu câu hỏi cần. Không chép từ trí nhớ hay từ LLM.
- Nếu đáp án phụ thuộc phiên bản luật, ghi rõ `as_of` và văn bản áp dụng trong `gold_answer`.
- `source`: `manual` (tự viết) hoặc `llm_draft_reviewed` (LLM sinh, đã duyệt tay). Câu `llm_draft_reviewed` bám sát từ ngữ trong chunk nên làm retrieval trông tốt hơn thực tế; nhóm `doi_thuong`, `bay_loi_thoi`, `ngoai_pham_vi` phải viết tay.
- Câu hỏi viết như người dùng thật, không lặp nguyên từ ngữ của điều luật.
- Mỗi `id` duy nhất, không câu nào trùng giữa dev và test. Mỗi nhóm có mặt ở cả hai tập.
- **`test.jsonl` đóng băng** sau khi chốt: chỉ thêm khi chưa chạy test lần nào.

## Validate
Trước khi chạy đánh giá, kiểm tra bằng script (`.venv/Scripts/python eval/validate_eval.py`; nếu chưa có thì viết): JSON hợp lệ, đủ trường, `group` hợp lệ, `gold_chunks` tồn tại trong `data/processed/`, `answerable=false` thì `gold_chunks` rỗng, không trùng id/câu hỏi, in bảng đếm theo nhóm và split.
