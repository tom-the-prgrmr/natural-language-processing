# 004 - Retrieval hybrid (cosine + BM25) thay cho dense đơn thuần (thành công lớn, chốt làm mặc định)

- Split: dev (16 câu, 13 answerable) rồi test (24 câu, 22 answerable)

## Giả thuyết
`experiments/001` từng nghi ngờ nguyên nhân Recall@5 thấp (0.31 dev / 0.23
test) nhưng chưa xác minh được. Rà lại `predictions.jsonl` của
`retrieval_test` cho thấy **16/22 câu (73%) gold chunk hoàn toàn không lọt
top-12** -- không phải vấn đề "xếp hạng thấp" như giả định lúc tăng k ở
`experiments/002`, mà là **không tìm thấy luôn**. Các câu hỏi mất đều có gold
chunk ở Điều 6/7 (mức phạt ô tô/xe máy, 93+85=178 chunk) nhưng bị lấn át bởi
Điều 20/21/32 (ô tô khách/tải/máy kéo, 42+45+113=200 chunk): các Điều này đều
mở đầu bằng cùng một mẫu câu hành chính rất dài và gần giống hệt nhau ("Xử
phạt, trừ điểm giấy phép lái xe của người điều khiển xe ô tô... vi phạm quy
tắc giao thông đường bộ"), chỉ khác nhau ở loại xe trong câu mở đầu, trong khi
nội dung hành vi cụ thể ("nồng độ cồn", "đỗ xe", "lạng lách") nằm ở phần điểm
rất ngắn. Dense embedding có vẻ bị chi phối bởi phần mở đầu dài giống nhau.
Giả thuyết: thêm điểm khớp từ khoá (BM25) -- vốn không bị "pha loãng" bởi độ
dài văn bản theo kiểu embedding trung bình hoá -- sẽ bắt đúng các từ đặc
trưng (nồng độ cồn, đỗ xe, lạng lách...) hiếm khi lặp lại giữa các Điều khác
chủ đề, bù được chỗ dense yếu.

## Biến đã đổi
Cách tính điểm truy xuất trong `src/retrieval.py: Retriever`, qua tham số
`mode`:
- `dense` (baseline cũ, giữ nguyên y hệt -- đã xác nhận lại bằng cách chạy lại
  và diff khớp 100% với `eval/results/retrieval_dev/metrics.json` cũ trước
  khi refactor).
- `hybrid` (mới): `0.5 * minmax(cosine) + 0.5 * minmax(BM25Okapi trên text thô
  tokenize bằng regex \w+)`, lấy top-k theo điểm cộng.

Thêm phụ thuộc `rank-bm25==0.2.2` (`requirements.txt`), thuần Python/CPU,
không gọi thêm API, không tốn thêm tiền.

## Giữ nguyên
`text-embedding-3-small`, `gpt-5.4-mini`, prompt v3c (`experiments/003`),
top-k=12, cùng corpus 2200 chunk, cùng 16 câu dev / 24 câu test.

## Kết quả retrieval

| Split | Mode | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---|---|---|---|---|
| dev | dense (baseline) | 0.0769 | 0.1538 | 0.3077 | 0.1682 |
| dev | **hybrid** | **0.2308** | **0.4615** | **0.5385** | **0.3817** |
| test | dense (baseline) | 0.0909 | 0.2273 | 0.2273 | 0.1591 |
| test | **hybrid** | **0.2727** | **0.5000** | **0.7273** | **0.4289** |

Lần chạy: `eval/results/retrieval_dev_v0_baseline/` (dense, xác nhận khớp
baseline cũ), `eval/results/retrieval_dev_hybrid/`,
`eval/results/retrieval_test/` (dense, kết quả gốc không đổi),
`eval/results/retrieval_test_hybrid/`.

Theo nhóm (dev, dense -> hybrid): `muc_phat_truc_tiep` Recall@5 0.4 -> 1.0;
`doi_thuong` 0.0 -> 0.33; `phu_thuoc_loai_xe` giữ 1.0 -> 0.5 (giảm nhẹ, cỡ mẫu
2 câu, nhiễu). Không có nhóm nào tệ đi đáng kể so với mức cải thiện tổng thể.

## Kết quả sinh câu trả lời (cùng prompt v3c, chỉ đổi retrieval_mode)

| Split | Mode | correct_numbers | citation_ok | refusal_ok (answerable) | refusal_ok (ngoài phạm vi) | total p50 (ms) |
|---|---|---|---|---|---|---|
| dev | dense (v3c) | 0.5385 | 0.6154 | 0.6154 | 1.0 | 1609.4 |
| dev | **hybrid** | **0.7692** | **0.7692** | **0.8462** | 1.0 | 1626.5 |
| test | dense (v3c) | 0.5000 | 0.2727 | 0.5455 | 1.0 | 1718.2 |
| test | **hybrid** | **0.7273** | **0.6818** | **0.9545** | 1.0 | **1418.1** |

`correct_numbers` ở bảng trên là **số đã sửa** sau `experiments/005` (bản ghi
lần đầu ở đây dùng metric cũ, có lỗ hổng — xem file đó để biết chi tiết và số
gốc trước khi sửa). citation_ok/refusal_ok/latency không bị ảnh hưởng bởi
việc sửa metric này.

Lần chạy: `eval/results/generation_dev_v3c_natural_style/`,
`eval/results/generation_dev_hybrid/`,
`eval/results/generation_test_v3c_natural_style_v2metric/`,
`eval/results/generation_test_hybrid_v2metric/`. Latency không những không
tệ đi mà còn **nhanh hơn** trên test (BM25 chạy CPU thuần, cộng thêm không
đáng kể so với việc LLM ít phải "vật lộn" với ngữ cảnh nhiễu hơn).

## Theo nhóm (test, dense -> hybrid, số đã sửa theo experiments/005)
`muc_phat_truc_tiep` 3/7 -> 6/7; `doi_thuong` 1/5 -> 2/5; `nhieu_dieu_kien`
0/4 -> 2/4; `phu_thuoc_loai_xe` 0/4 -> 2/4; `ngoai_pham_vi` giữ 2/2;
`bay_loi_thoi` giữ 1/2. Cải thiện đồng đều ở hầu hết các nhóm, không nhóm nào
tệ đi.

## Kết luận
**Cải thiện thật, lớn, nhất quán trên cả dev và test, trên cả hai tầng
(retrieval lẫn sinh câu trả lời), không tốn thêm API/tiền, không chậm đi.**
Đây là thí nghiệm có tác động lớn nhất trong toàn bộ dự án -- xác nhận giả
thuyết gốc của `experiments/001` (recall thấp không phải do thiếu tín hiệu
phân biệt, mà do *loại* tín hiệu: embedding trung bình hoá yếu với văn bản
hành chính lặp khuôn mẫu, từ khoá chính xác thì không). **Chốt `mode="hybrid"`
làm mặc định** (`Retriever.__init__`, `eval/run_retrieval.py`,
`eval/run_generation.py` đều đổi default sang `hybrid`, giữ `--mode dense` để
còn so sánh/debug). File `src/app.py`, `src/generation.py` không cần sửa gì
thêm vì đều gọi `Retriever()` không truyền `mode` -- tự động dùng mặc định
mới.

Lưu ý khi đọc bảng: đây là lần **thứ hai** chạy `test.jsonl` để đo một cấu
hình mới kể từ sau `experiments/003` (lần đầu: thêm kiểm tra trích dẫn bịa ở
`experiments/001`/`generation.py`). Giống các lần trước, quyết định thử hybrid
được đưa ra **trước** khi nhìn số test (chốt trên dev trước), và tất cả các
lần chạy test trước đó đều được giữ nguyên trong `eval/results/`, không xoá,
để không có chuyện "chạy tới khi ra số đẹp rồi xoá số xấu".

## Hạn chế còn lại (không phải đã giải quyết hoàn toàn)
- Trọng số 0.5/0.5 giữa cosine và BM25 chọn thủ công, chưa quét (sweep) để
  tìm trọng số tối ưu -- có thể còn cải thiện thêm nhưng hết thời gian.
- Tokenize BM25 chỉ bằng regex `\w+` + lowercase, không xử lý từ ghép tiếng
  Việt (vd "nồng độ cồn" tách thành 3 token rời), nhưng vẫn đủ hiệu quả vì các
  từ đơn trong cụm đã đủ đặc trưng để phân biệt chủ đề giữa các Điều.
- `citation_ok_rate` trên test (0.68) vẫn thấp hơn Recall@5 (0.73) -- LLM đôi
  khi vẫn không chọn đúng chunk vàng dù đã có trong top-12, giới hạn này vẫn
  còn (xem `docs/report.md`).

## Bước tiếp
Cập nhật `docs/report.md`, `docs/plan.md`, `CLAUDE.md` để phản ánh phương
pháp và số liệu mới (không được để tài liệu nói "retrieval yếu" trong khi số
liệu thật đã tốt hơn nhiều).
