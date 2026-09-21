# Kế hoạch thực hiện

Lập 2026-09-21. Hạn nộp **2026-10-01**. Trạng thái: `[ ]` chưa làm, `[x]` xong.

## Nguyên tắc sắp xếp
- Làm theo thứ tự phụ thuộc: corpus → tập đánh giá → retrieval → sinh câu trả lời → phân tích lỗi/cải tiến → triển khai → tài liệu.
- Chạy hệ thống end-to-end sớm (bản thô), rồi mới cải tiến. Đừng hoàn thiện từng khâu riêng lẻ.
- Tập test chỉ chạy **một lần** khi chốt cấu hình.
- Nếu trễ, cắt theo thứ tự ở cuối file, không cắt phân tích lỗi.

## Giai đoạn 0 — Chốt nền
- [x] Tải Luật 36, ND168, ND238 vào `data/raw/` (có SOURCES.md).
- [x] OCR ND238 bản nháp (`data/processed/ocr/nd238/`).
- [x] **0.1 Đối chiếu tay số liệu của ND238** với ảnh trang: mọi số tiền, điểm trừ, ngày hiệu lực đã khớp (SOURCES.md). Còn lại: trang 1, 2, 5, 8, 14 chưa xem ảnh, xem khi làm chunk phần đó.
- [ ] **0.2 Repo công khai:** đã quyết định đưa `data/raw/` (~9 MB) vào repo. Còn lại: commit đầu tiên (chờ xác nhận).
- [ ] **0.3 Chốt 3 quyết định mở** (mục cuối file).

## Giai đoạn 1 — Corpus
- [ ] **1.1 Làm sạch văn bản:** script `src/ingest/clean.py` đọc `data/raw/` → `data/processed/`. Sửa lỗi khoảng trắng do link (`k hi`, `đ )`), ký tự Cyrillic lẫn chữ Latin, bỏ header/footer web. Xong khi: đếm đúng ND168 Điều 1–55, Luật 36 Điều 1–89, ND238 Điều 1–21.
- [ ] **1.2 Chunk theo Điều/Khoản/Điểm:** `src/ingest/chunk.py` → `data/processed/chunks.jsonl`, ID theo `docs/legal-data.md`, metadata gồm văn bản, điều, tiêu đề điều, khoản, điểm, **ngày hiệu lực theo từng điều khoản**. Xong khi: không chunk rỗng, chunk tách theo điểm lặp lại câu dẫn có mức phạt.
- [ ] **1.3 Mô hình phiên bản luật:** hàm trả về "ND168 gốc" hoặc "ND168 sau ND238" theo ngày hành vi. ND238 chỉ thay các điểm/khoản nêu tên; phần còn lại giữ nguyên ND168. Gắn nhãn "bản tự hợp nhất" vì chưa có văn bản hợp nhất chính thức.
- [ ] **1.4 Test và lấy mẫu:** `tests/test_chunk.py` (parser, ID, đếm điều) và so tay 10 chunk ngẫu nhiên với nguồn.

## Giai đoạn 2 — Tập đánh giá
Phần **tốn công người nhất**, không thể tự động hoá hết vì nhãn phải tra tay (xem `docs/eval-spec.md`).
- [ ] **2.1 Script validate** `eval/validate_eval.py` (schema, chunk vàng tồn tại, không trùng, đếm theo nhóm).
- [ ] **2.2 Soạn nháp câu hỏi:** LLM sinh nháp cho nhóm `muc_phat_truc_tiep` và `phu_thuoc_loai_xe`; nhóm `doi_thuong`, `bay_loi_thoi`, `ngoai_pham_vi` **viết tay**.
- [ ] **2.3 Tra và duyệt đáp án vàng** từng câu với `data/raw/`. Xong khi: mọi câu có `gold_chunks`, `gold_answer`, `verified_by`.
- [ ] **2.4 Chia dev/test** giữ đủ nhóm ở cả hai tập. Mục tiêu ~100 câu (dev ~30, test ~70); tối thiểu 60 nếu gấp. **Đóng băng test.**

## Giai đoạn 3 — Retrieval baseline
- [ ] **3.1 Chọn và cài embedding** (xem quyết định mở), dựng index cho `chunks.jsonl`.
- [ ] **3.2 Retrieval:** dense; thêm BM25 và hybrid nếu kịp. Lọc theo phiên bản/ngày hiệu lực.
- [ ] **3.3 Script metric retrieval** `eval/`: Recall@1/3/5, MRR trên dev. Lưu kết quả vào `eval/results/`.
- [ ] Xong khi: có con số baseline thật, lưu kèm cấu hình và seed.

## Giai đoạn 4 — Sinh câu trả lời baseline
- [ ] **4.1 Prompt + LLM OpenAI:** chỉ dùng ngữ cảnh truy xuất, output JSON (câu trả lời, trích dẫn, cờ từ chối), từ chối khi thiếu căn cứ.
- [ ] **4.2 Metric sinh:** đúng đáp án (khớp cả hai đầu khoảng phạt), trích dẫn đúng (so ID bằng code), từ chối đúng/nhầm, faithfulness. Nếu dùng LLM chấm, tự kiểm ~20 câu.
- [ ] **4.3 Chạy trên dev**, có baseline end-to-end đầu tiên (hỏi đáp một lượt).
- [ ] **4.4 Hội thoại nhiều lượt (chatbot):** nhận lịch sử tin nhắn; viết lại câu hỏi tiếp nối thành câu hỏi độc lập trước khi tìm kiếm (ví dụ "còn ô tô thì sao?" sau một câu về xe máy); hỏi lại khi thiếu thông tin quyết định mức phạt (loại xe). Xong khi: chạy được một hội thoại mẫu 3 lượt, có test với LLM mock.

## Giai đoạn 5 — Phân tích lỗi và cải tiến
Phần đề chấm nặng nhất.
- [ ] **5.1 Phân tích lỗi:** bảng lỗi theo nhóm câu hỏi và theo nguyên nhân (không tìm ra / tìm ra nhưng sinh sai / nhầm loại xe / nhầm phiên bản / bịa số / từ chối nhầm), kèm 3–5 ca cụ thể.
- [ ] **5.2 Ablation chunking:** chunk theo khoản so với cố định độ dài, đổi đúng một biến.
- [ ] **5.3 Một cải tiến từ lỗi thật** (ví dụ hybrid/rerank, sửa prompt, lọc phiên bản), so trước/sau trên dev. Ghi theo `docs/experiment-template.md`.
- [ ] **5.4 Chạy test một lần** với cấu hình cuối, ghi kết quả. Không chỉnh gì sau đó.

## Giai đoạn 6 — Phần tự nghĩ thêm
Chọn **một** trong các ứng viên ở `docs/00-idea.md`, khuyến nghị: **kiểm tra trích dẫn tự động + xử lý phiên bản luật** (điều/khoản model nêu có thật trong ngữ cảnh không; cảnh báo mốc 15/08/2026 và các mốc 2028/2029). Ghi rõ đâu là ý riêng.

## Giai đoạn 7 — Triển khai
- [ ] **7.1 FastAPI:** endpoint `/chat` nhận `messages` (lịch sử hội thoại), trả câu trả lời, trích dẫn, cờ từ chối/hỏi lại, thời gian từng khâu. Phía client giữ lịch sử; server không lưu phiên.
- [ ] **7.2 Web demo dạng khung chat** (hiện hội thoại, mỗi câu trả lời kèm trích dẫn bấm xem được), có cảnh báo "công cụ tham khảo, không phải tư vấn pháp lý".
- [ ] **7.3 Đo latency** p50/p95 từng khâu (retrieval, sinh).

## Giai đoạn 8 — Tài liệu
- [ ] `README.md` chạy lại từ đầu (setup → ingest → index → eval → serve); thử làm theo trên môi trường sạch.
- [ ] Báo cáo mô tả đủ 7 mục, sơ đồ kiến trúc và luồng end-to-end (Mermaid).
- [ ] Slide HTML một file.
- [ ] Review độc lập toàn bộ theo `docs/submission-checklist.md` (rò rỉ test, số liệu mồ côi, mức phạt sai).

## Giai đoạn 9 — Nộp
- [ ] Quay video 5–10 phút: bài toán → dữ liệu → cách làm → kết quả → lỗi và bài học → demo chạy thật.
- [ ] Đẩy repo công khai, nộp video và link GitHub trên Google Classroom.

## Nếu trễ, cắt theo thứ tự
1. Giảm tập đánh giá xuống ~60 câu; bỏ nhóm hội thoại nhiều lượt khỏi tập đánh giá (vẫn giữ tính năng, chỉ demo).
2. Bỏ hybrid/rerank, chỉ giữ dense; bỏ LLM chấm, chấm bằng code.
3. Bỏ tự host LLM và các mục điểm cộng (Triton, dashboard).
4. Web demo tối giản (một trang HTML gọi API).
**Không cắt:** tập đánh giá có nhãn tra tay, phân tích lỗi, so sánh trước/sau bằng số thật, đối chiếu ND238.

## Rủi ro chính
| Rủi ro | Giảm bằng |
|---|---|
| Viết và tra 100 câu đáp án tốn thời gian nhất | Bắt đầu sớm; chốt dev (30 câu) trước để chạy retrieval sớm |
| OCR ND238 sai số | Bước 0.1; không dùng chunk ND238 trong test khi chưa đối chiếu |
| Sai chồng phiên bản luật (ND168/ND238, mốc 2028/2029) | Metadata ngày hiệu lực theo từng điều khoản, test riêng |
| Hội thoại nhiều lượt làm việc đánh giá phức tạp hơn | Nhóm `nhieu_luot` nhỏ (~10 hội thoại), chấm riêng, không lẫn vào số đo chính |
| Chi phí và độ trễ API | Cache kết quả embedding; test dùng mock |

## Quyết định mở (cần chốt ở bước 0.3)
1. **Embedding:** chạy local (bge-m3 hoặc multilingual-e5, vừa 4 GB VRAM, cần cài thêm thư viện lớn) hay dùng API OpenAI (đã có khoá, nhanh, đỡ cài đặt)? Tên model cụ thể phải kiểm tra lại trước khi chọn.
2. **LLM sinh câu trả lời:** model OpenAI nào (đã liệt kê danh sách; chưa chốt).
3. **Ai soạn nháp câu hỏi đánh giá:** tôi soạn nháp rồi bạn duyệt, hay bạn tự viết hoàn toàn nhóm đời thường và bẫy?
