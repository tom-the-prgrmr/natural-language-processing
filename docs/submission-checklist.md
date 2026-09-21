# Checklist nộp bài (đối chiếu đề trong `docs/assignment.md`)

Dùng thủ công trước hạn 2026-10-01.

Với mỗi mục: kiểm tra bằng cách **đọc file thật**, đánh dấu `có / thiếu / chưa đủ`, và ghi đường dẫn. Không đánh dấu "có" theo trí nhớ.

## 7 mục chính
1. Problem statement: vấn đề, người dùng, metric và lý do (`docs/01-requirements.md`, `docs/report.md`).
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
Báo cáo bảng ngắn: mục | trạng thái | đường dẫn | việc còn lại. Sắp xếp việc còn lại theo mức ảnh hưởng đến điểm và thời gian còn tới hạn.
