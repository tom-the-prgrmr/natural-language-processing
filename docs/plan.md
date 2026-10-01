# Kế hoạch thực hiện

Bản kế hoạch ban đầu (9 giai đoạn, ~100 câu đánh giá, hybrid retrieval, ablation đầy đủ) không kịp thực hiện đúng tiến độ nên đã viết lại, cắt phạm vi mạnh để vẫn đi trọn vòng đời (đúng yêu cầu cốt lõi của đề) với chất lượng thấp hơn, thay vì làm dở một phạm vi lớn.

Trạng thái: `[ ]` chưa làm, `[x]` xong.

## Quyết định đã chốt
- Embedding: **API OpenAI** (`text-embedding-3-small`), không thử local nữa — bỏ ablation embedding.
- LLM sinh câu trả lời: **`gpt-5.4-mini`**.
- Soạn câu hỏi đánh giá: Claude soạn nháp, người dùng duyệt nhanh (không tự viết tay toàn bộ nhóm đời thường/bẫy như dự định trước — không đủ thời gian; đánh đổi này được ghi nhận là hạn chế trong báo cáo).
- **Bỏ:** reranker, ablation chunking, LLM-as-judge, tự host LLM local, Triton/dashboard.
- **Quay lại giữa chừng (không còn đủ thời gian lúc đầu nên định bỏ, sau đó vẫn kịp làm vì cải thiện quá lớn):** hybrid BM25+dense — xem `experiments/004-hybrid-bm25.md`.
- **Giữ (không cắt thêm):** trích dẫn bắt buộc, tách dev/test, phân tích lỗi thật, một cải tiến có so sánh trước/sau, cảnh báo "tham khảo, không tư vấn pháp lý".

## Phạm vi rút gọn

### Corpus, tập đánh giá, retrieval, sinh câu trả lời, cải tiến
- [x] **1.1 Làm sạch + chunk** → `src/ingest/clean.py`, `src/ingest/chunk.py` → `data/processed/chunks.jsonl` (2200 chunk: L36 887, 168 1243, 238 70). Chunk mức khoản (+ sub-chunk theo điểm, lặp câu dẫn). ND238 chunk theo "Điều của ND238" + mục con, có `amends_dieu`; không dựng bản hợp nhất (quyết định cắt phạm vi, prompt sinh câu trả lời tự chọn bản theo ngày hiệu lực).
- [x] **1.2 Test tối thiểu:** `tests/test_chunk.py`, 5 test pass (đếm điều đúng 55/89, không rỗng/trùng, 2 chunk biết trước đáp án khớp, tỉ lệ khoản "0" < 20%).
- [x] **2. Tập đánh giá: 40 câu** (dev 16 / test 24, đúng tỉ trọng 12/8/6/6/4/4 theo nhóm) → `data/eval/{dev,test}.jsonl`, sinh bởi `data/eval/build_seed.py`, kiểm bằng `eval/validate_eval.py` (0 lỗi). Claude tra trực tiếp `chunks.jsonl` lấy số liệu thật cho `gold_answer`, **CHƯA được người dùng duyệt** — ghi trong `verified_by` của từng câu, cần duyệt trước khi dùng số liệu final report.
- [x] **3. Retrieval:** `src/retrieval.py` (embed API `text-embedding-3-small` + cosine numpy, cache `data/processed/embeddings.npz`), `eval/run_retrieval.py`. Baseline dense trên dev: Recall@1 0.077, @3 0.154, @5 0.308, MRR 0.168. Thử 2 cách rút gọn text embed, cả hai đều tệ hơn baseline (`experiments/001`). Sau đó rà lại nguyên nhân gốc (73% câu test gold chunk không lọt top-12, nhầm giữa Điều 6/7 và Điều 20/21/32 có tiêu đề hành chính giống nhau) và thêm **hybrid BM25+cosine** (`experiments/004-hybrid-bm25.md`) — **chốt làm mặc định**: test Recall@5 0.227→**0.727**, MRR 0.159→**0.429**. Thêm **mở rộng truy vấn văn nói → thuật ngữ luật** (`experiments/007`) sau khi phát hiện câu ví dụ README trả lời sai do lệch từ vựng — chốt mặc định: test MRR 0.429→**0.613**, Recall@5 →**0.773**.
- [x] **4. Sinh câu trả lời:** `src/generation.py` — prompt ép trích dẫn + từ chối + hỏi lại khi thiếu loại xe, output JSON qua `response_format=json_object`. Hội thoại nhiều lượt: query retrieval = ghép các lượt user trước + câu hỏi hiện tại (không tách bước rewrite riêng). **Phần tự nghĩ thêm:** kiểm tra trích dẫn tự động — nếu model trích dẫn id không nằm trong chunk đã truy xuất (bịa), tự động ép `refused=True` thay vì để lọt câu trả lời trông có căn cứ nhưng thực ra không (xem code, không phải chỉ ở eval). Mở rộng thêm mức thứ hai (`experiments/006`): mọi số tiền trong câu trả lời phải có trong chunk được trích.
- [x] **5. Phân tích lỗi + cải tiến:** 6 thí nghiệm thật + 1 lần sửa cách đo, log ở `experiments/`:
  - `001`: thử rút gọn text embed (bỏ tiêu đề Điều, rồi bỏ câu dẫn khoản) để tăng recall — **cả hai đều tệ hơn baseline**, giữ nguyên baseline (kết quả âm tính, vẫn ghi lại).
  - `002`: tăng k đưa vào bước sinh câu trả lời 8→12 — **cải thiện thật** (đúng số liệu 0.38→0.46, trích dẫn đúng 0.31→0.46 trên dev). Chốt k=12.
  - `003`: prompt văn phong tự nhiên — câu lặp miễn trừ 8→0 trên dev, độ đúng không giảm (chênh lệch trong nhiễu ~2/13 câu).
  - `004`: **hybrid BM25+cosine retrieval** — cải thiện lớn nhất dự án, đồng thời trên retrieval lẫn sinh câu trả lời, cả dev lẫn test, không tốn thêm API/latency (xem bảng ở mục 3 và file thí nghiệm). Chốt làm mặc định.
  - Đã chạy **test nhiều lần, mỗi lần một thay đổi đã chốt trước trên dev** (không tinh chỉnh dựa trên số test): lần đầu (`generation_test/`), thêm kiểm tra trích dẫn bịa (`generation_test_v1_no_citation_check/` → bản giữ), đổi prompt v3c (`generation_test_v3c_natural_style/`), đổi retrieval hybrid (`generation_test_hybrid/`, `retrieval_test_hybrid/`). **Số liệu mới nhất** (prompt v3c + hybrid, đã sửa metric theo `005`): correct_numbers 0.73, citation_ok 0.68, refusal_ok (answerable) 0.95, refusal_ok (ngoài phạm vi) 1.0. Tất cả các lần chạy trước đều giữ nguyên trong `eval/results/`, không xoá.
  - `005`: sửa lỗ hổng chỉ số `correct_numbers_rate` (chấm `True` oan cho câu không có số tiền để so, vd ngưỡng km/h, điểm trừ GPLX) — tính lại từ `predictions.jsonl` đã lưu, không gọi lại LLM. Xem `experiments/005-fix-correct-numbers-metric.md`.
  - `006`: kiểm tra trích dẫn mức nội dung (số tiền phải có trong chunk được trích); làm lộ và sửa một lỗi dữ liệu có từ đầu ("40.000. 000" do thẻ HTML nội tuyến). Giữ, nhưng test lặp cho thấy gốc lỗi ở retrieval.
  - `007`: mở rộng truy vấn văn nói → thuật ngữ luật — test MRR 0.429→0.613, `correct_numbers` 0.727→0.773, câu ví dụ README 0/15→15/15 đúng. Chốt mặc định. **Số liệu mới nhất** (test): correct_numbers 0.77, citation_ok 0.64 (strict) / 0.91 (đúng khoản), refusal_ok (answerable) 0.95, refusal_ok (ngoài phạm vi) 1.0.
  - **Chưa làm:** viết bảng lỗi/phân tích theo nhóm dạng văn xuôi cho báo cáo (số liệu thô đã có trong `predictions.jsonl`); quét trọng số kết hợp cosine/BM25 (đang cố định 0.5/0.5).
  - **Hạn chế biết trước:** không cố định seed/temperature cho lời gọi LLM, nên có nhiễu giữa các lần chạy giống hệt cấu hình.

### Triển khai, tài liệu, review
- [x] **7. FastAPI** endpoint `/chat` (`src/app.py`) + **web demo khung chat tối giản** (`web/index.html`, một trang HTML/JS gọi `/chat`, giữ lịch sử hội thoại phía client) + đo latency thật qua `eval/run_api_latency.py` trên 16 câu dev: **p50 1706ms, p90 2742ms, max 3105ms** (`eval/results/api_latency/`).
- [x] **8. Tài liệu:** `README.md` (chạy lại từ đầu; đã tự chạy lại toàn bộ trên bản sao sạch gồm đúng các file sẽ commit + venv mới + không cache embedding, mọi lệnh đạt; chưa thử trên máy/HĐH khác hẳn — ghi rõ trong README), `docs/report.md` (đủ 7 mục, nêu thẳng phần đã cắt), `docs/architecture.md` (2 sơ đồ Mermaid), `docs/slides.html` (slide một file, dùng phím mũi tên chuyển slide).
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
| Không kịp tự chạy lại README trên máy sạch | Đã chạy lại trên bản sao sạch (cùng máy) — đạt; phần "máy/HĐH khác" vẫn chưa kiểm, nêu thẳng trong README |
