# Checklist nộp bài (đối chiếu đề trong `docs/assignment.md`)

Dùng thủ công trước khi nộp bài.

Với mỗi mục: kiểm tra bằng cách **đọc file thật**, đánh dấu `có / thiếu / chưa đủ`, và ghi đường dẫn. Không đánh dấu "có" theo trí nhớ.

## 7 mục chính
1. Problem statement: vấn đề, người dùng, metric và lý do (`docs/00-idea.md`, `docs/report.md`).
2. Data: nguồn, số lượng, chia dev/test, mất cân bằng nhóm, xử lý dữ liệu và lý do.
3. Method: mô hình/LLM chọn và lý do, cấu hình thật, thiết kế prompt hoặc tham số.
4. Evaluation và phân tích lỗi: metric đúng, các ca sai cụ thể, điểm chung lặp lại theo nhóm.
5. Cải tiến: ít nhất một hướng từ lỗi thật, so trước/sau bằng số liệu (có nhật ký trong `experiments/`).
6. Phần tự nghĩ thêm: ít nhất một ý riêng, nêu rõ đâu là ý riêng.
7. Deployment: FastAPI chạy được, web demo, có đo thời gian phản hồi.

## Sản phẩm nộp
- Repo GitHub **công khai**, có toàn bộ code (xử lý dữ liệu, gọi LLM/huấn luyện, đánh giá, API, web demo).
- README chạy lại được từ đầu: thử làm theo từng lệnh trên môi trường sạch.
- Sơ đồ kiến trúc và luồng end-to-end.
- Tài liệu mô tả đủ 7 mục.
- Bộ slide HTML.
- Video 5–10 phút trên Google Classroom, có link GitHub trong phần nộp: bài toán → dữ liệu → cách làm → kết quả → lỗi và bài học → demo chạy thật.

## Kiểm tra của dự án
- Mọi con số trong README/báo cáo/slide truy được về file kết quả thật.
- `test.jsonl` chỉ chạy sau khi chốt cấu hình; không bị rò vào prompt hay few-shot.
- Không có khoá API/`.env` trong repo; không có dữ liệu cá nhân.
- Cảnh báo "công cụ tham khảo, không phải tư vấn pháp lý" có trong demo và README.
- Ghi rõ nguồn văn bản luật, ngày truy cập, và phần ND238 đã đối chiếu tay hay chưa.
- Điểm yếu và hướng cải thiện tiếp theo được nói thẳng.

## Kết quả

Đã kiểm bằng cách đọc file thật / chạy lệnh thật (`gh repo view`, `git ls-files`, `pytest`, `ruff`), không đánh dấu theo trí nhớ.

| Mục | Trạng thái | Đường dẫn | Việc còn lại |
|---|---|---|---|
| 1. Problem statement | có | `docs/00-idea.md`, `docs/report.md` §1 | — |
| 2. Data | có | `docs/report.md` §2, `data/raw/SOURCES.md`, `docs/legal-data.md` | — |
| 3. Method | có | `docs/report.md` §3, `src/retrieval.py`, `src/generation.py` | — |
| 4. Evaluation + phân tích lỗi | có | `docs/report.md` §4, `eval/results/` | — |
| 5. Cải tiến | có | `docs/report.md` §5, `experiments/001`, `experiments/002`, `experiments/003` | — |
| 6. Phần tự nghĩ thêm | có | `docs/report.md` §6 (kiểm tra trích dẫn bịa) | — |
| 7. Deployment | có | `docs/report.md` §7, `src/app.py`, `web/index.html`, `eval/results/api_latency/` | — |
| Repo GitHub công khai | có | `gh repo view` → `PUBLIC` | — |
| README chạy lại được | có — đã chạy lại toàn bộ trên bản sao sạch (chỉ file sẽ commit, venv mới, không cache embedding), mọi lệnh đạt | `README.md` mục "Giới hạn đã biết" | chưa thử trên máy/HĐH khác hẳn (đã ghi rõ trong README) |
| Sơ đồ kiến trúc | có | `docs/architecture.md` (2 sơ đồ Mermaid) | — |
| Slide HTML | có | `docs/slides.html` | — |
| Video 5–10 phút | **chưa** | — | quay, kèm link GitHub khi nộp trên Google Classroom |
| Không lộ `.env`/khoá API | có | `git ls-files \| grep .env` rỗng, `.gitignore` | — |
| Cảnh báo "tham khảo, không tư vấn pháp lý" | có | `web/index.html` header, `README.md` (prompt không lặp lại trong từng câu trả lời, xem `experiments/003`) | — |
| Nguồn luật + ngày truy cập + trạng thái đối chiếu OCR | có | `data/raw/SOURCES.md`, `docs/legal-data.md` | — |
| Test đóng băng không bị rò | có | `test.jsonl` chỉ dùng ở `eval/run_*.py --split test`, không đưa vào prompt | — |
| Điểm yếu nói thẳng | có | `docs/report.md` mục "Giới hạn đã biết", `README.md` | — |

**Việc còn lại duy nhất trước khi nộp: quay video.**
