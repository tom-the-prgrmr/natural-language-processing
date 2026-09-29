# Đề bài: Mini project cuối module NLP

Trích nguyên văn từ bài tập Google Classroom (AI Engineer K08). Tiêu chí chấm: 5 tiêu chí, 100 điểm (trang gốc không liệt kê chi tiết trọng số).

MỤC TIÊU
Đây là bài tập lớn tổng kết module NLP. Mục tiêu không phải đạt điểm số cao nhất, mà là đi trọn vẹn vòng đời phát triển một sản phẩm NLP thật: từ bài toán, dữ liệu, xây dựng mô hình, đánh giá, phân tích lỗi, cải tiến, đến triển khai. Đây là một yêu cầu khá lớn và đầy đủ, đúng chất một dự án thật. Cứ làm hết khả năng của mình, quan trọng nhất là qua quá trình đó bạn tự nhận ra mình còn thiếu gì và cần học thêm gì, đừng để số lượng yêu cầu làm bạn lo lắng.
CHỌN ĐỀ TÀI
Tự chọn 1 bài toán NLP mà bạn thấy hứng thú: phân loại văn bản, nhận diện thực thể, tóm tắt hoặc sinh văn bản, tìm kiếm ngữ nghĩa, chatbot, hoặc kết hợp vài dạng lại với nhau. Vài gợi ý:
- Phân loại cảm xúc hoặc phát hiện spam trên review tiếng Việt
- Trích xuất thực thể trên văn bản chuyên ngành như hoá đơn, tin tuyển dụng, văn bản pháp luật
- Tóm tắt văn bản tiếng Việt hoặc sinh văn bản có kiểm soát
- Tìm kiếm ngữ nghĩa trên một tập tài liệu (FAQ, sản phẩm, tài liệu nội bộ), có thể mở rộng thành chatbot trả lời dựa trên tài liệu
- Hoặc đề tài khác tự đề xuất, miễn có dữ liệu thật và khả thi trong thời gian làm bài
Dùng dataset công khai (HuggingFace, Kaggle, các bộ dữ liệu tiếng Việt có sẵn...) hoặc tự thu thập, gán nhãn quy mô nhỏ.
CÁCH TIẾP CẬN: TỰ HUẤN LUYỆN HAY DÙNG LLM
Chọn 1 trong 2 hướng, hoặc kết hợp cả hai:
1. Fine-tune một pretrained model (BERT, PhoBERT, RoBERTa...) trên dữ liệu của mình, full fine-tune hoặc PEFT đều được.
2. Dùng LLM có sẵn thay vì tự train, ví dụ Gemma, Qwen, DeepSeek, Llama, hoặc qua API như OpenAI, Gemini, Groq. Chọn hướng này thì phần "huấn luyện" chuyển thành: thiết kế prompt và các kỹ thuật kiểm soát đầu vào, đầu ra để model trả lời ổn định, đúng định dạng (system prompt rõ ràng, few-shot, ép output theo cấu trúc...), và so sánh vài cách làm khác nhau bằng số liệu thật.
Tự host được LLM, tức chạy Gemma/Qwen/DeepSeek trên máy của mình thay vì chỉ gọi API, là một điểm cộng lớn vì đòi hỏi hiểu thêm về tối ưu và triển khai.
YÊU CẦU CHÍNH
1. Problem statement: bài toán giải quyết vấn đề gì, cho ai dùng, đo thành công bằng metric nào và vì sao. Đây là phần thể hiện bạn hiểu đúng bài toán trước khi bắt tay vào code.
2. Data: nguồn dữ liệu, số lượng, cách chia train/val/test, có mất cân bằng lớp không, có xử lý hay tăng cường dữ liệu gì không và vì sao.
3. Method: mô hình hoặc LLM bạn chọn, lý do chọn, và cách bạn huấn luyện hoặc kiểm soát nó (tham số fine-tune, hoặc thiết kế prompt). Ghi lại quá trình thật, không bịa số.
4. Evaluation và phân tích lỗi: dùng đúng metric cho dạng bài toán của bạn. Xem qua các trường hợp mô hình làm sai, tìm ra điểm chung lặp lại (sai nhiều ở nhóm dữ liệu nào, tình huống nào), từ đó hiểu vì sao sai chứ không chỉ báo cáo một con số tổng.
5. Cải tiến: từ lỗi tìm được, thử ít nhất một hướng cải thiện cụ thể và so sánh trước/sau bằng số liệu thật.
6. Phần tự nghĩ thêm (quan trọng, ảnh hưởng lớn đến điểm cao): ít nhất một ý tưởng của riêng bạn, không có sẵn trong bài giảng. Có thể là một kỹ thuật khác đem ra thử, một góc phân tích lỗi riêng, một tính năng thêm vào demo, hoặc một hướng cải tiến bạn đề xuất cho tương lai dù chưa kịp làm. Hiểu rõ cái khó của bài toán và biết còn có thể thử gì tiếp theo quan trọng hơn việc đạt con số đẹp nhất.
7. Deployment: đóng gói mô hình hoặc pipeline LLM thành một API (FastAPI là đủ) và có web demo đơn giản để test trực tiếp. Đo thử tốc độ phản hồi. Dùng Triton, đo tải, hoặc dựng dashboard giám sát là điểm cộng nâng cao, không bắt buộc, dựng được API chạy ổn định đã là đạt yêu cầu cơ bản.
SẢN PHẨM NỘP
GitHub repository công khai, gồm:
- Toàn bộ code: notebook hoặc script xử lý dữ liệu, huấn luyện hoặc gọi LLM, đánh giá, API, web demo
- README hướng dẫn chạy lại từ đầu
- Sơ đồ kiến trúc và luồng xử lý end to end
- Tài liệu mô tả đầy đủ các mục ở trên
- Một bộ slide tóm tắt dự án (dựng bằng HTML với sự hỗ trợ của AI cho nhanh cũng được)
Video trình bày 5 đến 10 phút, nộp trên Google Classroom: trình bày mạch lạc từ bài toán, dữ liệu, cách làm, kết quả, lỗi và bài học rút ra, đến demo sản phẩm chạy thật. Dán kèm link GitHub trong phần nộp bài.
LƯU Ý
Không cần đạt kết quả tốt nhất hay dùng model lớn nhất. Trọng tâm chấm điểm là hiểu đúng vòng đời phát triển, biết lý do đằng sau mỗi lựa chọn, biết rõ điểm còn yếu và hướng cải thiện tiếp theo. Đây chính là năng lực phân biệt một AI Engineer thật với người chỉ biết gọi API có sẵn.
