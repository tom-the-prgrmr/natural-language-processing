# 001 - Rút gọn text đưa vào embedding (thất bại, giữ baseline)

- Split: dev (13 câu answerable=true)

## Giả thuyết
Baseline (v0) embed nguyên `text` của chunk, trong đó tiêu đề Điều (dài, có khi
>50 từ) bị lặp lại y hệt ở mọi chunk con cùng Điều (một Điều có tới ~40 chunk
con). Đoán rằng tiêu đề lặp lại làm loãng vector, khiến các chunk cùng Điều
trông giống nhau hơn là khác nhau theo nội dung vi phạm cụ thể -> bỏ tiêu đề
(v1) hoặc bỏ thêm câu dẫn "Phạt tiền từ X đến Y đồng đối với...sau đây:" lặp
lại giữa các điểm cùng khoản (v2) sẽ tăng recall.

## Biến đã đổi
Nội dung text dùng để tính embedding (`text_embed`), qua 3 cấu hình:
- v0: `text` đầy đủ (tiêu đề Điều + câu dẫn khoản + nội dung điểm)
- v1: bỏ tiêu đề Điều, giữ câu dẫn khoản + nội dung điểm
- v2: giữ tiêu đề Điều, bỏ câu dẫn khoản (chỉ tiêu đề + nội dung điểm)

## Giữ nguyên
Model `text-embedding-3-small`, top-k=5, cosine, cùng 13 câu dev, cùng corpus 2200 chunk.

## Kết quả
| Cấu hình | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|
| v0 (baseline, giữ nguyên) | 0.0769 | 0.1538 | **0.3077** | 0.1500 |
| v1 (bỏ tiêu đề) | 0.0000 | 0.1538 | 0.1538 | 0.0641 |
| v2 (bỏ câu dẫn khoản) | 0.0769 | 0.2308 | 0.2308 | 0.1538 |

Lần chạy: `eval/results/retrieval_dev_v0_full_title/` (v0, bản lưu tay trước khi
sửa) và `eval/results/retrieval_dev/` (kết quả v0 sau khi revert, khớp lại
đúng số trên — xác nhận revert đúng).

## Theo nhóm (v0 so với v1)
`phu_thuoc_loai_xe` giảm mạnh nhất khi bỏ tiêu đề: 1.0 -> 0.0. Hợp lý: câu hỏi
loại này luôn nói rõ "ô tô" hay "xe máy", và tiêu đề Điều 6/Điều 7 chính là chỗ
duy nhất phân biệt hai loại xe một cách tường minh trong text. Bỏ tiêu đề làm
mất tín hiệu quan trọng nhất cho đúng nhóm câu hỏi này.

## Kết luận
**Giả thuyết bị bác bỏ theo cả hai hướng thử.** Tiêu đề Điều tuy lặp lại nhưng
mang tín hiệu phân biệt loại xe quan trọng hơn phần bị "loãng". Giữ nguyên v0
làm baseline chính thức.

Nguyên nhân recall thấp (0.31 ở baseline) có vẻ không nằm ở việc "tiêu đề lặp
lại" mà ở chỗ khác — quan sát thủ công cho thấy nhiều câu (ví dụ hỏi về nồng độ
cồn ô tô) bị lẫn sang Điều 21 (xe tải chở hàng, không liên quan alcohol) dù nội
dung 2 Điều khác hẳn nhau về chủ đề. Nghi ngờ: embedding tiếng Việt của
`text-embedding-3-small` với các đoạn luật ngắn, nhiều thuật ngữ hành chính lặp
lại (phạt tiền, đồng, hành vi vi phạm) có độ phân giải ngữ nghĩa hạn chế ở cấp
điểm/khoản. Chưa xác minh thêm do hết thời gian.

## Bước tiếp
Không tiếp tục sửa cách embed (đã hết ngân sách thời gian cho hướng này). Bù
lại ở tầng sinh câu trả lời: tăng k lên 8 (thay vì 5) khi truy xuất cho bước
generation, và bắt buộc model chỉ trả lời khi có căn cứ rõ trong ngữ cảnh, từ
chối/nêu không chắc khi ngữ cảnh không khớp — coi retrieval yếu là một giới hạn
đã biết, ghi rõ trong báo cáo, thay vì cố sửa tiếp trong thời gian còn lại.
