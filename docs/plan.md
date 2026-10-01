# Kế hoạch thực hiện

Bản kế hoạch ban đầu (9 giai đoạn, ~100 câu đánh giá, hybrid retrieval, ablation đầy đủ) không kịp thực hiện đúng tiến độ nên đã viết lại, cắt phạm vi mạnh để vẫn đi trọn vòng đời (đúng yêu cầu cốt lõi của đề) với chất lượng thấp hơn, thay vì làm dở một phạm vi lớn.

Trạng thái: `[ ]` chưa làm, `[x]` xong.

## Quyết định đã chốt
- Embedding: **API OpenAI** (`text-embedding-3-small`), không thử local nữa — bỏ ablation embedding.
- LLM sinh câu trả lời: **`gpt-5.4-mini`**.
- Soạn câu hỏi đánh giá: Claude soạn nháp, người dùng duyệt nhanh (không tự viết tay toàn bộ nhóm đời thường/bẫy như dự định trước — không đủ thời gian; đánh đổi này được ghi nhận là hạn chế trong báo cáo).
- **Bỏ:** hybrid BM25+dense, reranker, ablation chunking, LLM-as-judge, tự host LLM local, Triton/dashboard.
- **Giữ (không cắt thêm):** trích dẫn bắt buộc, tách dev/test, phân tích lỗi thật, một cải tiến có so sánh trước/sau, cảnh báo "tham khảo, không tư vấn pháp lý".

## Phạm vi rút gọn

### Corpus, tập đánh giá, retrieval, sinh câu trả lời, cải tiến
- [x] **1.1 Làm sạch + chunk** → `src/ingest/clean.py`, `src/ingest/chunk.py` → `data/processed/chunks.jsonl` (2200 chunk: L36 887, 168 1243, 238 70). Chunk mức khoản (+ sub-chunk theo điểm, lặp câu dẫn). ND238 chunk theo "Điều của ND238" + mục con, có `amends_dieu`; không dựng bản hợp nhất (quyết định cắt phạm vi, prompt sinh câu trả lời tự chọn bản theo ngày hiệu lực).
- [x] **1.2 Test tối thiểu:** `tests/test_chunk.py`, 5 test pass (đếm điều đúng 55/89, không rỗng/trùng, 2 chunk biết trước đáp án khớp, tỉ lệ khoản "0" < 20%).
- [x] **2. Tập đánh giá: 40 câu** (dev 16 / test 24, đúng tỉ trọng 12/8/6/6/4/4 theo nhóm) → `data/eval/{dev,test}.jsonl`, sinh bởi `data/eval/build_seed.py`, kiểm bằng `eval/validate_eval.py` (0 lỗi). Claude tra trực tiếp `chunks.jsonl` lấy số liệu thật cho `gold_answer`, **CHƯA được người dùng duyệt** — ghi trong `verified_by` của từng câu, cần duyệt trước khi dùng số liệu final report.
- [x] **3. Retrieval:** `src/retrieval.py` (embed API `text-embedding-3-small` + cosine numpy, cache `data/processed/embeddings.npz`), `eval/run_retrieval.py`. Baseline trên dev (13 câu answerable): **Recall@1 0.077, @3 0.154, @5 0.308, MRR 0.15**. Thử 2 cách rút gọn text embed để cải thiện, cả hai đều tệ hơn baseline (xem `experiments/001-embed-text-tieu-de.md`) — giữ nguyên baseline, ghi nhận recall thấp là giới hạn đã biết, bù bằng k lớn hơn + bắt buộc từ chối khi thiếu căn cứ ở bước sinh câu trả lời.
- [x] **4. Sinh câu trả lời:** `src/generation.py` — prompt ép trích dẫn + từ chối + hỏi lại khi thiếu loại xe, output JSON qua `response_format=json_object`. Hội thoại nhiều lượt: query retrieval = ghép các lượt user trước + câu hỏi hiện tại (không tách bước rewrite riêng). **Phần tự nghĩ thêm:** kiểm tra trích dẫn tự động — nếu model trích dẫn id không nằm trong chunk đã truy xuất (bịa), tự động ép `refused=True` thay vì để lọt câu trả lời trông có căn cứ nhưng thực ra không (xem code, không phải chỉ ở eval).
- [x] **5. Phân tích lỗi + cải tiến:** 2 thí nghiệm thật, log ở `experiments/`:
  - `001`: thử rút gọn text embed (bỏ tiêu đề Điều, rồi bỏ câu dẫn khoản) để tăng recall — **cả hai đều tệ hơn baseline**, giữ nguyên baseline (kết quả âm tính, vẫn ghi lại).
  - `002`: tăng k đưa vào bước sinh câu trả lời 8→12 — **cải thiện thật** (đúng số liệu 0.38→0.46, trích dẫn đúng 0.31→0.46 trên dev). Chốt k=12.
  - Đã chạy **test một lần, đóng băng** (`eval/results/{retrieval,generation}_test/`): correct_numbers 0.55, citation_ok 0.23, refusal_ok (answerable) 0.64, refusal_ok (ngoài phạm vi) 1.0. Test chạy 2 lần vì thêm tính năng kiểm tra trích dẫn (đã lên kế hoạch từ trước, không phải sửa vì thấy fail) sau lần chạy đầu — cả 2 lần đều giữ lại (`generation_test_v1_no_citation_check/`), không giấu.
  - **Chưa làm:** viết bảng lỗi/phân tích theo nhóm dạng văn xuôi cho báo cáo (số liệu thô đã có trong `predictions.jsonl`).
  - **Hạn chế biết trước:** không cố định seed/temperature cho lời gọi LLM, nên có nhiễu giữa các lần chạy giống hệt cấu hình (thấy rõ ở 2 lần chạy test).

### Triển khai, tài liệu, review
- [x] **7. FastAPI** endpoint `/chat` (`src/app.py`) + **web demo khung chat tối giản** (`web/index.html`, một trang HTML/JS gọi `/chat`, giữ lịch sử hội thoại phía client) + đo latency thật qua `eval/run_api_latency.py` trên 16 câu dev: **p50 1706ms, p90 2742ms, max 3105ms** (`eval/results/api_latency/`).
- [x] **8. Tài liệu:** `README.md` (chạy lại từ đầu, tự kiểm từng lệnh trên máy hiện tại — chưa thử máy sạch hoàn toàn, ghi rõ trong README), `docs/report.md` (đủ 7 mục, nêu thẳng phần đã cắt), `docs/architecture.md` (2 sơ đồ Mermaid), `docs/slides.html` (slide một file, dùng phím mũi tên chuyển slide).
- [x] **Review nhanh** theo `docs/submission-checklist.md` — bảng kết quả đã điền, mọi mục đều "có" trừ video.

### Nộp
- [ ] Quay video 5–10 phút, đẩy code còn lại lên `main`, nộp link trên Google Classroom.

## Nếu vẫn không kịp (cắt tiếp theo thứ tự)
1. Web demo bỏ hẳn giao diện chat nhiều lượt, chỉ còn form hỏi 1 câu.
2. Tập test giảm xuống 16 câu (bằng dev).
3. Bỏ phần "cải tiến có so sánh" — chỉ báo baseline và nêu hướng cải thiện trong báo cáo (không được bỏ phân tích lỗi).
**Tuyệt đối không bỏ:** trích dẫn bắt buộc, tách dev/test, phân tích lỗi có số liệu thật, cảnh báo pháp lý.

## Rủi ro
| Rủi ro | Xử lý |
|---|---|
| Tập đánh giá 40 câu do Claude soạn phần lớn, ít người duyệt tay | Ghi rõ trong báo cáo là hạn chế do thời gian; không tự nhận là tập lớn/đầy đủ |
| Không có mô hình hợp nhất ND168+ND238 | Ghi rõ trong README/báo cáo: hệ thống lọc theo ngày hiệu lực ở tầng retrieval + prompt, chưa có văn bản hợp nhất |
| Không kịp tự chạy lại README trên máy sạch | Nêu thẳng trong báo cáo, không nhận "đã kiểm chứng" nếu chưa làm |
