# Nhật ký thí nghiệm

Tạo `experiments/NNN-<tên-ngắn>.md` (NNN tăng dần). Mẫu:

```markdown
# NNN - <tên>

- Ngày: YYYY-MM-DD
- Split: dev | test
- Giả thuyết: <vì sao nghĩ đổi X sẽ cải thiện Y, dựa trên lỗi nào từ lần chạy nào>
- Biến đã đổi (chỉ một): <ví dụ chunk theo khoản -> chunk 512 token>
- Giữ nguyên: <embedding, LLM, top-k, prompt, seed, tập câu hỏi>
- Lần chạy đối chứng: eval/results/<tên>   Lần chạy thử nghiệm: eval/results/<tên>

## Kết quả
| Metric | Trước | Sau | Số câu |
|---|---|---|---|
(số lấy nguyên từ metrics.json)

## Theo nhóm
<nhóm nào tốt lên/kém đi, số câu mỗi nhóm>

## Kết luận
<đã xác nhận/bác bỏ giả thuyết? chênh lệch có lớn hơn nhiễu của cỡ mẫu không?>

## Bước tiếp
<một việc cụ thể>
```

## Quy tắc
- Ghi cả thí nghiệm thất bại. Đó là nội dung tốt cho phần phân tích lỗi và bài học.
- Chỉ ghi số có trong file kết quả; đường dẫn tới file đó phải có trong nhật ký.
- Nếu đổi nhiều hơn một biến, ghi rõ đây không phải so sánh có kiểm soát và không rút kết luận nhân quả.
- Cập nhật `experiments/README.md` thành bảng mục lục: số, tên, giả thuyết một dòng, kết luận một dòng.
