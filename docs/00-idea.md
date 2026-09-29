# Ý tưởng: Chatbot tra cứu mức phạt giao thông (RAG)

Yêu cầu gốc của đề: `docs/assignment.md`.

## 1. Bài toán
Người dân hỏi bằng ngôn ngữ đời thường ("vượt đèn đỏ xe máy phạt bao nhiêu?") và cần câu trả lời **đúng mức phạt, đúng điều khoản, kèm trích dẫn**. Nguồn trả lời trên mạng thường sai, lỗi thời hoặc lẫn giữa xe máy và ô tô.

Hệ thống dạng **chatbot**: nhận hội thoại nhiều lượt (hiểu câu hỏi tiếp nối, hỏi lại khi thiếu loại xe), tìm điều khoản liên quan trong văn bản pháp luật (semantic search), rồi để LLM trả lời **chỉ dựa trên điều khoản tìm được**, có trích dẫn, và từ chối khi câu hỏi ngoài phạm vi.

Người dùng: người lái xe phổ thông. Đây là công cụ tham khảo, không phải tư vấn pháp lý (phải có cảnh báo trong demo).

## 2. Vì sao chọn
- Nhu cầu thật: Nghị định 168/2024 (hiệu lực 01/01/2025) và **Nghị định 238/2026 sửa đổi (hiệu lực 15/08/2026)** vừa thay đổi quy định, người dân đang cần tra cứu.
- Nối trực tiếp buổi 47–49 (semantic search, embeddings, RAG).
- Có chỗ cho phân tích lỗi rõ ràng (bịa mức phạt, lấy sai điều khoản, nhầm loại xe, dùng luật lỗi thời).
- Phải tự dựng tập đánh giá, đây là phần "tự gán nhãn quy mô nhỏ" mà đề cho phép.

Đã cân nhắc và loại: phát hiện tin lừa đảo (thiếu dữ liệu công khai), ABSA review điện thoại (an toàn nhưng chung chung), kiểm duyệt bình luận độc hại.

## 3. Ràng buộc
- **GPU: GTX 1650, 4 GB VRAM**. Python 3.11.9. Không có tesseract/torch sẵn.
  - Embedding cỡ bge-m3 (~0,6B) chạy được.
  - LLM tự host chỉ khả thi ở cỡ 1,5–3B lượng tử hoá 4 bit (llama.cpp/Ollama). Cỡ 7B không nằm gọn trong VRAM. Tên model cụ thể cần kiểm tra lại khi chọn.
  - Phương án dự phòng: gọi API (Gemini/Groq/OpenAI) cho phần sinh câu trả lời, giữ embedding chạy local.
- Văn bản luật thay đổi theo thời gian, nên corpus phải có metadata phiên bản và ngày hiệu lực.

## 4. Dữ liệu
Đã tải về `data/raw/` (xem `data/raw/SOURCES.md`): Luật 36/2024/QH15, Nghị định 168/2024, Nghị định 238/2026.
Vấn đề mở: ND238 chỉ có bản scan, cần OCR và đối chiếu tay. Chưa có bản hợp nhất ND168 sau sửa đổi.

## 5. Thiết kế tập đánh giá (tóm tắt)
- ~100 câu (dev ~30, test ~70; tối thiểu 60 nếu gấp), chia nhóm để phân tích lỗi: mức phạt trực tiếp (~30), câu đời thường (~20), phụ thuộc loại xe (~15), nhiều điều kiện/hình phạt bổ sung (~15), ngoài phạm vi (~10), bẫy lỗi thời/tiền đề sai (~10).
- Nhãn mỗi câu: `gold_chunks` (ID chunk theo điều/khoản/điểm), `gold_answer` (ghi khoảng phạt đủ hai đầu), `answerable`.
- Nhãn do người viết và tra tay. LLM chỉ hỗ trợ sinh câu hỏi nháp rồi duyệt tay; ghi rõ phần nào do LLM sinh.
- Metric: Recall@k và MRR (retrieval); đúng đáp án, có căn cứ (faithfulness), trích dẫn đúng (generation); tỉ lệ từ chối đúng và từ chối nhầm.
- Tập test chỉ chạy ở cuối, không chỉnh gì dựa trên nó.

## 6. Hướng kỹ thuật (dự kiến, chưa chốt)
- Chunk theo cấu trúc pháp lý (điều/khoản/điểm) kèm metadata (văn bản, điều, khoản, điểm, hiệu lực). Ablation so với chunk cố định.
- Embedding đa ngôn ngữ + BM25 (hybrid), có thể thêm reranker.
- LLM sinh câu trả lời với prompt ép: chỉ dùng ngữ cảnh, phải trích dẫn, từ chối khi không đủ căn cứ, output JSON.
- FastAPI + web demo đơn giản, đo latency từng bước.

## 7. Ứng viên cho "phần tự nghĩ thêm"
1. Kiểm tra trích dẫn tự động: điều/khoản model nêu có thật sự nằm trong ngữ cảnh đã truy xuất không.
2. Xử lý phiên bản luật: ưu tiên điều khoản đã sửa đổi (ND238), cảnh báo mốc 15/08/2026 với hành vi xảy ra trước đó.
3. Truy vấn cần thông tin còn thiếu (loại xe?): hỏi lại thay vì đoán.
4. Đo mức lệch giữa LLM-as-judge và chấm tay trên ~20 câu.
5. Hướng tương lai (chưa làm): tra cứu theo hình ảnh biển báo, đối chiếu tin giao thông mới.

## 8. Đối chiếu tiêu chí của đề
| Yêu cầu | Đáp ứng bằng |
|---|---|
| Problem statement | Mục 1–2 |
| Data | Corpus luật + tập đánh giá tự dựng, chia dev/test |
| Method | Hybrid retrieval + LLM có kiểm soát; so sánh vài cấu hình |
| Evaluation + phân tích lỗi | Metric mục 5, phân tích theo nhóm câu hỏi |
| Cải tiến | Từ lỗi tìm được (ví dụ chunking, rerank, prompt), so trước/sau |
| Tự nghĩ thêm | Mục 7 |
| Deployment | FastAPI, web demo, đo latency; tự host LLM là điểm cộng |
| Nộp | Repo, README, sơ đồ, tài liệu, slide HTML, video 5–10 phút |

## 9. Các bước thực hiện
Xem `docs/plan.md`.

## 10. Rủi ro
- OCR ND238 sai chữ số → mức phạt sai. Giảm bằng đối chiếu tay.
- Tập đánh giá dễ bám sát từ ngữ trong chunk nếu sinh bằng LLM → tự viết tay các nhóm đời thường, bẫy, ngoài phạm vi.
- 4 GB VRAM giới hạn LLM local → giữ phương án API dự phòng.
- Dữ liệu luật có thể được sửa đổi tiếp → ghi ngày truy cập và phiên bản.

## 11. Câu hỏi mở
- ~~LLM local hay API?~~ Đã chọn: dùng API OpenAI cho phần sinh câu trả lời. Tự host LLM local (điểm cộng) là mục tùy chọn nếu còn thời gian; embedding vẫn chạy local. Model OpenAI cụ thể chưa chốt.
- OCR ND238: đã OCR bằng mô hình thị giác (bản nháp), còn phải đối chiếu tay (xem `data/raw/SOURCES.md`).
- Có cần bản hợp nhất ND168 + ND238, hay chỉ xử lý theo từng văn bản kèm cảnh báo?
