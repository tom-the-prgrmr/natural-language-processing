# Chatbot tra cứu mức phạt giao thông (RAG) — Mini project cuối module NLP

Bài nộp AI Engineer K08. Đề bài: `docs/assignment.md`. Ý tưởng, ràng buộc: `docs/00-idea.md`. Kế hoạch thực hiện: `docs/plan.md`. Nguồn dữ liệu: `data/raw/SOURCES.md`.

Hệ thống dự kiến (dạng chatbot, hội thoại nhiều lượt): hỏi đáp về xử phạt giao thông đường bộ Việt Nam trên Luật 36/2024/QH15, Nghị định 168/2024/NĐ-CP và Nghị định 238/2026/NĐ-CP (sửa ND168, hiệu lực 15/08/2026; một số điều khoản hiệu lực muộn hơn, xem SOURCES.md). Retrieval theo điều/khoản, LLM chỉ trả lời dựa trên ngữ cảnh truy xuất, có trích dẫn, từ chối khi ngoài phạm vi. Công cụ tham khảo, không phải tư vấn pháp lý.

## Trạng thái hiện tại
Có pipeline đầy đủ: làm sạch + chunk (`data/processed/chunks.jsonl`), tập đánh giá 40 câu (`data/eval/`, **chưa được người dùng duyệt tay**), retrieval (`src/retrieval.py`), sinh câu trả lời có trích dẫn + tự phát hiện trích dẫn bịa (`src/generation.py`), test (`tests/`), 2 thí nghiệm ghi lại ở `experiments/`, FastAPI `/chat` + demo web tối giản (`src/app.py`, `web/index.html`), báo cáo + sơ đồ + slide (`docs/report.md`, `docs/architecture.md`, `docs/slides.html`), review theo `docs/submission-checklist.md` (bảng kết quả đã điền). **Chưa có:** video nộp bài.

## Commands
Chạy từ thư mục gốc. Luôn dùng python của venv dự án, không cài gì vào Python toàn cục.

| Việc | Lệnh |
|---|---|
| Tạo venv | `python -m venv .venv` |
| Cài phụ thuộc | `.venv/Scripts/python -m pip install -r requirements-dev.txt` |
| OCR PDF scan (gọi API OpenAI, tốn tiền, cần `.env`) | `.venv/Scripts/python src/ingest/ocr_pdf.py <pdf> --model <id> --out <dir>` (xem `--help`, `--list-models`) |
| Lint | `.venv/Scripts/ruff check .` |
| Format | `.venv/Scripts/ruff format .` |
| Test | `.venv/Scripts/pytest` |
| Typecheck | TODO: xác nhận (chưa chọn công cụ) |
| Dev server (API + web demo) | `.venv/Scripts/uvicorn src.app:app --reload --port 8000`, demo tại `http://127.0.0.1:8000/` |
| Đo latency API thật | `.venv/Scripts/python eval/run_api_latency.py --base-url http://127.0.0.1:8000` (cần server đang chạy) |

## Stack
Python 3.11.9. Phụ thuộc chính: `openai`, `pymupdf`, `pypdf`, `python-dotenv`, `numpy`, `fastapi`, `uvicorn` (`requirements.txt`, phiên bản cố định); dev: `ruff`, `pytest` (`requirements-dev.txt`). Cấu hình ruff ở `pyproject.toml` (chỉ `target-version`, còn lại mặc định). Máy: Windows 11. Embedding (`text-embedding-3-small`) và sinh câu trả lời (`gpt-5.4-mini`) đều qua API OpenAI (xem `docs/plan.md` phần quyết định). Git: nhánh `main`, remote `github.com/tom-the-prgrmr/natural-language-processing`; chưa có CI.

## Cấu trúc thư mục
```
data/raw/        văn bản gốc, bất biến (có SOURCES.md)          [đã có]
data/processed/  văn bản đã làm sạch + chunk (clean/, chunks.jsonl) [đã có]
data/eval/       dev.jsonl, test.jsonl, build_seed.py             [đã có]
src/ingest/      clean.py, chunk.py, ocr_pdf.py                    [đã có]
src/             retrieval.py, generation.py, app.py (FastAPI)     [đã có]
web/             index.html (demo chat tối giản, gọi /chat)        [đã có]
eval/            run_retrieval.py, run_generation.py, run_api_latency.py, validate_eval.py, results/ [đã có]
tests/           test_chunk.py                                     [đã có]
experiments/     001, 002 (log thí nghiệm)                         [đã có]
docs/            assignment.md, 00-idea.md, plan.md, submission-checklist.md, ...
```

## Quy tắc
1. **Không bịa số.** Mọi con số trong báo cáo/slide phải truy được về một file kết quả chạy thật trong `experiments/` hoặc `eval/`. Chưa chạy thì ghi "chưa đo".
2. **Nhãn luật do người tra tay.** Mức phạt, điều, khoản trong đáp án vàng phải đối chiếu văn bản gốc; không dùng LLM sinh nhãn rồi dùng luôn.
3. **Tập test đóng băng.** Chỉnh chunking, prompt, top-k chỉ dựa trên `dev.jsonl`; chạy `test.jsonl` khi chốt cấu hình, sau đó không sửa test để cải số.
4. **Mọi câu trả lời mức phạt phải kèm trích dẫn** (văn bản, điều, khoản, điểm) và nêu văn bản/phiên bản còn hiệu lực.
5. Thí nghiệm so sánh đổi **một biến**, cố định seed, ghi cấu hình và kết quả (mẫu: `docs/experiment-template.md`).
6. Tài liệu viết tiếng Việt, ngắn gọn; định danh trong code bằng tiếng Anh.

## Không được làm
- Không commit hay đọc `.env` (khoá API chỉ nằm ở `.env`, mẫu: `.env.example`).
- Không sửa `data/raw/` (quy ước: `docs/legal-data.md`) và không sửa `data/eval/test.jsonl` sau khi đóng băng.
- Không cài phụ thuộc vào Python toàn cục; không thêm phụ thuộc mà không ghi vào `requirements*.txt`.
- Không gọi API OpenAI trong test; dùng mock.

## Tài liệu quy ước
- Dữ liệu luật, ID chunk, phiên bản: `docs/legal-data.md`. Tập đánh giá (schema, nhóm, gán nhãn): `docs/eval-spec.md`. Checklist nộp bài: `docs/submission-checklist.md`. Báo cáo đủ 7 mục: `docs/report.md`. Sơ đồ: `docs/architecture.md`. Slide: `docs/slides.html`.
