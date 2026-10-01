# 005 - Sửa lỗ hổng chỉ số `correct_numbers_rate` (sửa cách đo, không phải sửa model)

Không phải thí nghiệm đổi biến mô hình/prompt như 001-004 -- đây là sửa một
lỗ hổng trong **cách đo** đã tự nhận trong `docs/report.md` ("Hạn chế của
chính chỉ số correct_numbers_rate"), ghi lại theo đúng tinh thần "không bịa
số" vì nó làm đổi số liệu chính thức đã công bố. Sửa qua **3 vòng** (bắt được
2 bug ngay trong lúc sửa, nhờ viết test trước), ghi lại cả quá trình thay vì
chỉ bản cuối, để đúng tinh thần "ghi quá trình thật, không bịa số".

## Vấn đề gốc
`eval/run_generation.py: numbers_covered()` (bản cũ) chỉ so khớp số tiền dạng
`x.xxx.xxx`. Các câu hỏi phân biệt bằng ngưỡng khác (tốc độ km/h, tuổi, chiều
cao mét, số điểm trừ GPLX) không có số tiền nào để so -- `gold_nums` rỗng ->
hàm trả `True` mặc định -- nên `correct_numbers=True` ngay cả khi model trả
lời/từ chối sai hoàn toàn với các câu này. Phát hiện khi rà `predictions.jsonl`
của `generation_test_hybrid`: nhiều câu có `correct_numbers=True` dù model nói
thẳng "chưa có đoạn nào nêu rõ số điểm bị trừ..." (q23) hoặc bỏ sót ngưỡng tốc
độ trong câu trả lời (q20).

## Vòng 1: thêm matcher theo đơn vị
Thêm `UNIT_NUM_RE` (bắt số đi kèm `km/h`, `miligam`, `mililít`, `mg/lít`,
`tuổi`, `m`) và `POINT_DEDUCT_RE` (bắt riêng `trừ X điểm` GPLX).

**Bug 1 (bắt được trước khi chạy thật):** thử gộp luôn `điểm` vào
`UNIT_NUM_RE`, kết quả sai ngay -- cụm trích dẫn "khoản 9 điểm b" cũng có số
đứng ngay trước chữ "điểm" (khoản 9), bị hiểu nhầm thành "9 điểm GPLX". Kiểm
bằng cách chạy regex trên toàn bộ 40 `gold_answer`, đọc tay từng câu khớp.
Sửa: tách riêng `POINT_DEDUCT_RE`, yêu cầu có chữ "trừ" đứng trước mới khớp.

## Vòng 2: bug logic "variants" (bắt được nhờ viết test trước)
Chuẩn hoá số có "0" đệm đầu (`"04"` ~ `"4"`) bằng một hàm trả về set 2 dạng.
Cách ghép đầu tiên: gộp phẳng mọi dạng của mọi số vào một set `gold_nums` rồi
yêu cầu **tất cả** phần tử trong set phải có mặt trong answer. Viết
`tests/test_eval_metrics.py` trước khi tin dùng -- test
`test_point_deduction_caught` fail ngay: gold có "04 điểm", answer viết "4
điểm" (không có "0" đệm) vẫn bị chấm sai, vì hàm đòi cả "04" lẫn "4" cùng có
mặt thay vì chỉ cần một trong hai dạng. Sửa: đổi cấu trúc dữ liệu từ một set
phẳng sang danh sách các set (mỗi số gốc một set các dạng chấp nhận được),
yêu cầu mỗi set có *ít nhất một* dạng khớp.

**Bug 2 (bắt được nhờ chính test vừa sửa ở trên, test thứ hai trong cùng hàm
fail tiếp):** sau khi sửa bug 1, test vẫn fail ở phần "thiếu điểm trừ phải bị
chấm sai" -- hoá ra số "4" (dạng rút gọn của "04") tình cờ **trùng với một
phần của chuỗi tiền "4.000.000"** đã có sẵn trong answer, nên so chuỗi con
đơn thuần luôn trả `True` dù answer không hề nhắc tới "điểm". Đây là lỗi bản
chất của cách so chuỗi con với số ngắn (1-2 chữ số rất dễ trùng ngẫu nhiên).
Sửa: với số có ngữ cảnh (đơn vị/điểm trừ), không so chuỗi con số trần nữa, mà
dùng lại chính regex đã trích xuất để tìm số **cùng ngữ cảnh** đó trong
answer (vd phải thấy lại mẫu "trừ N điểm" trong answer, không chỉ là chữ số
N xuất hiện ở đâu đó).

## Vòng 3: "mét" vs "m" (phát hiện khi chạy lại sau vòng 2)
Sau khi sửa bug 2 và chạy lại trên dữ liệu thật, phát hiện q18 đổi kết quả
đúng/sai qua lại bất thường -- rà tay: gold ghi "1,35 **m**", model (cả dense
lẫn hybrid) viết "1,35 **mét**" (cùng nghĩa, khác cách viết), nhưng
`UNIT_NUM_RE` dùng `m\b` (ranh giới từ ngay sau "m") không khớp bên trong
"mét" vì "é" vẫn là ký tự chữ. Thêm `mét` làm một nhánh riêng trong regex,
viết thêm `test_meter_unit_word_spelled_out_is_accepted` để khoá lại hành vi
đúng.

Tính lại từ `predictions.jsonl` đã lưu, không gọi lại LLM/API (không tốn
tiền, không đổi câu trả lời thật của model) bằng `eval/rescore_generation.py`,
ghi ra thư mục mới hậu tố `_v2metric`, giữ nguyên thư mục gốc.

## Kết quả cuối cùng (sau cả 3 vòng sửa)

| Split | Mode | correct_numbers (metric cũ) | correct_numbers (metric đã sửa) | Số câu đổi |
|---|---|---|---|---|
| dev | dense (v3c) | 0.5385 | 0.5385 | 0/13 |
| dev | hybrid | 0.7692 | 0.7692 | 0/13 |
| test | dense (v3c) | 0.6364 | **0.5000** | 3/22 |
| test | hybrid | 0.8636 | **0.7273** | 3/22 |

Lần chạy: `eval/results/generation_{dev,test}_{v3c_natural_style,hybrid}_v2metric/`.
`tests/test_eval_metrics.py`: 6 test, bao gồm 1 test khoá hành vi của mỗi bug
đã bắt được (money match, speed threshold, point deduction, không nhầm cấu
trúc trích dẫn, "mét" vs "m", mặc định true khi không có số cần so).

3 câu đổi trên test (dense lẫn hybrid đều cùng 3 id q20/q23/q24 -- xem
`predictions.jsonl` từng thư mục; q18 **không đổi** nhờ đã sửa ở vòng 3):
- **q20** ("ô tô chạy 25 km/h vượt quá tốc độ..."): gold nêu "25 km/h (nằm
  trong khoảng 20-35 km/h)"; model chỉ nhắc "25 km/h", không nhắc lại khoảng
  "20-35" làm căn cứ -- đúng số tiền nhưng thiếu một phần ngữ cảnh gold yêu
  cầu. Siết chặt hợp lý (hạn chế còn lại: chỉ bắt được đầu trên của khoảng).
- **q23**, **q24** ("...trừ mấy điểm"): model tự nhận "chưa có đoạn nào nêu
  rõ số điểm bị trừ" -- đúng số tiền phạt nhưng rõ ràng thiếu thông tin so
  với gold (có nêu "trừ 04/10 điểm"). Bản metric cũ chấm `True` oan.

## Kết luận
Phát hiện thật, không phải lỗi vặt: metric cũ **chấm quá tay** (lenient) cho
đúng loại câu hỏi mà metric này sinh ra để bắt lỗi -- và bản sửa đầu tiên của
chính tôi cũng có bug tương tự (chấm quá chặt rồi lại quá lỏng), chỉ lộ ra
nhờ viết test trước và đọc kỹ từng assertion fail thay vì tin ngay kết quả
"trông hợp lý". Sau khi sửa đúng cả 3 vòng, **kết luận chính của
`experiments/004` (hybrid tốt hơn dense rõ rệt) vẫn giữ nguyên** -- test:
dense 0.50 -> hybrid 0.727, chênh lệch vẫn rất lớn, chỉ là cả hai số tuyệt
đối đều giảm so với bản gốc (0.6364->0.50 và 0.8636->0.7273) vì giờ đo chặt
hơn và đúng hơn. **Chốt dùng metric đã sửa cho mọi lần chạy sau**
(`eval/run_generation.py` đã sửa trực tiếp, có test bảo vệ). Cập nhật lại số
liệu trong `docs/report.md`, `docs/slides.html`, `docs/plan.md` theo bản đã
sửa, không giữ số liệu cũ (lạc quan hơn thực tế) làm số chính thức.

## Hạn chế còn lại
- `UNIT_NUM_RE`/`POINT_DEDUCT_RE` vẫn là heuristic theo từ khoá cố định, chưa
  tổng quát (vd số trong khoảng "20-35 km/h" chỉ bắt được đầu trên nếu không
  có chỗ khác nhắc riêng đầu dưới -- xem q29 trong `experiments/004`); các
  cách viết tắt/đồng nghĩa khác ngoài "mét" (vd viết hoa, dấu cách khác) có
  thể vẫn bị bỏ sót.
- Vẫn không phải LLM-as-judge; không đánh giá được văn phong/mức độ đầy đủ
  ngoài việc có nhắc đúng con số hay không.
- Bài học quy trình: nên viết test trước cho mọi hàm chấm điểm *trước khi*
  dùng nó để công bố số liệu, không phải sau khi đã thấy số "trông hợp lý".
