# 002 - Tăng top-k đưa vào bước sinh câu trả lời (thành công, chốt k=12)

- Split: dev (16 câu, 13 answerable)

## Giả thuyết
Retrieval baseline (xem `experiments/001-...`) yếu: Recall@5 chỉ 0.31, một số
câu (đặc biệt nhóm nồng độ cồn) gold chunk còn không lọt vào top-15. Thử kiểm
tra ở `eval/run_retrieval.py --k 15`: các ca thất bại nặng nhất (q14, q15, q21,
q38) **vẫn không tìm thấy** dù nới k tới 15 — nên không kỳ vọng riêng việc nới
k sẽ sửa hết, nhưng với các ca gold nằm ở hạng 6-15 (ví dụ q22, hạng 9), việc
truyền nhiều ứng viên hơn cho LLM ở bước sinh câu trả lời có thể giúp LLM tự
chọn đúng chunk trong số nhiều lựa chọn, thay vì retrieval phải đúng ngay ở
top-5/top-8.

## Biến đã đổi
`k` (số chunk truyền vào prompt sinh câu trả lời): 8 -> 12.

## Giữ nguyên
Model sinh: `gpt-5.4-mini`. Model embedding: `text-embedding-3-small`. Cùng 16
câu dev, cùng prompt hệ thống, cùng retriever/index.

## Kết quả
| k | correct_numbers | citation_ok | refusal_ok (answerable) | refusal_ok (unanswerable) |
|---|---|---|---|---|
| 8  | 0.3846 | 0.3077 | 0.6154 | 1.0 |
| 12 | **0.4615** | **0.4615** | **0.6923** | 1.0 |

Lần chạy: `eval/results/generation_dev_k8/`, `eval/results/generation_dev_k12/`.

## Theo nhóm (k=8 -> k=12)
`muc_phat_truc_tiep`: 0.4 -> 0.6. `nhieu_dieu_kien`: 0.0 -> 0.5. Các nhóm khác
không đổi hoặc đã đúng/sai từ trước — cỡ mẫu 2-5 câu/nhóm nên không tách rời
được tín hiệu khỏi nhiễu ở mức nhóm, chỉ số tổng (13 câu answerable) đáng tin
hơn.

## Kết luận
Cải thiện thật trên cả 3 chỉ số chính, không đổi refusal_ok cho câu ngoài phạm
vi (vẫn 1.0, không bị "quá đà" trả lời liều khi k lớn hơn). **Chốt k=12** làm
cấu hình chính thức (`src/generation.py: TOP_K = 12`). Latency p50 tổng ~2.1s
(k=12) so với ~2.3s (k=8) — nằm trong nhiễu, không tệ đi đáng kể dù ngữ cảnh
dài hơn.

Giới hạn còn lại (không sửa tiếp do hết thời gian): 4/13 câu answerable vẫn sai
ngay cả ở k=12, chủ yếu do retrieval không đưa được gold chunk vào top-12 cho
các câu về nồng độ cồn mức cao và câu văn nói (doi_thuong). Xem
`docs/report.md` phần phân tích lỗi.

## Bước tiếp
Chạy cấu hình này (k=12) một lần trên test, đóng băng, dùng làm số liệu chính
thức cho báo cáo.
