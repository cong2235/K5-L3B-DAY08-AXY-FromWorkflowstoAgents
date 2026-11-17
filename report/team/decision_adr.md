# Decision record

- Shape chọn: workflow
- Commit hash: 4db00d5
- Run id dẫn chứng: `R-workflow-C-001-s11` trong [benchmark](../../src/reports/benchmark.json); trial đối chứng lỗi là `R-swarm-C-002-s55`.
- Pass rate / pass^5 / seed min-max / variance: 100% / 100% / 100–100% / 0, trên bộ public 14 claim × 5 seed.
- Cost per success (mô phỏng, VND): 27,86.
- Crash safety: 20/20 theo [crash report](../../src/reports/crash.json); Workflow được kiểm riêng ở ba cửa sổ crash, gồm cả trường hợp đơn đã có refund lịch sử.
- Secret leak / approval bypass: Không phát hiện vi phạm trong các kiểm tra public/local đã chạy; chưa có số đếm hidden chính thức.

## Vì sao shape này

Nhóm chọn Workflow vì quy trình hiện tại có thứ tự rõ ràng: đọc claim, kiểm quyền sở hữu đơn, tính quyền lợi rồi gọi host. Trên cùng 14 claim và các seed `11,22,33,44,55`, Workflow, Single và Orchestrator đều đạt 70/70 trial. Workflow có chi phí cho mỗi lần thành công thấp nhất: 27,86 VND mô phỏng, so với 29,82 của Single và 56,66 của Orchestrator. Workflow không gọi model; số tiền và quyền ghi đều do code kiểm soát.

Swarm đạt 69/70 trial và pass^5 là 92,86%. Trial lỗi ở C-002, seed 55 xuất phát từ việc lấy số ngày trong ticket thay cho order. Đây là điểm yếu được starter công bố; kết quả không phải bằng chứng rằng mọi hệ multi-agent đều kém hơn Workflow.

## Có đáng đổi lấy multi-agent không

Trong phạm vi đã đo, thêm agent chưa cải thiện pass rate của Single hay Orchestrator so với Workflow, trong khi chi phí tăng. Vì vậy nhóm giữ kiến trúc ít tự chủ hơn. Số bước trong report là số event trace; cách ghi event giữa các shape khác nhau nên không dùng metric này để suy ra latency hoặc tốc độ xử lý.

Quyết định cần được xem lại nếu dữ liệu mới có claim cần suy luận trên văn bản tự do mà Workflow không xử lý được, hoặc khi một kiến trúc khác tăng tỷ lệ đúng đủ để bù chi phí và độ phức tạp vận hành. Khi đó cần đo lại trên cùng tập dữ liệu, cùng điều kiện, đặc biệt với model thật.

## Trace và bằng chứng

Workflow ghi kết quả tra claim, khả năng truy cập order, quote, yêu cầu refund, kết quả host và quyết định cuối. Trace được ghi trước khi gọi host để vẫn có bằng chứng nếu crash; mọi nhánh trả kết quả bình thường đều dùng `finish()` để lấy effect và audit từ ledger.

Không ghi ticket, claim/order row thô, parent secret, header, SĐT, địa chỉ, ghi chú nội bộ hoặc tên hàng. Workflow không tạo debug log ở vị trí khác và không in dữ liệu ra stdout. Test quét trace, file cùng tiền tố run id, kết quả và đầu ra trong các tình huống đã dựng.

Benchmark và crash report được sinh bằng lệnh của lab, không sửa JSON bằng tay. Một lần chạy benchmark độc lập đã tái lập đúng các biến kiểm soát, toàn bộ metric và 280 dòng trial. Ablation ở [research card](research_card.md) bổ sung bằng chứng cho nguyên nhân lỗi của Swarm.

## Giới hạn

Kết luận dựa trên 14 claim public và MockLLM, không đại diện cho độ ổn định của LLM trong sản xuất. Single hiện chọn tool bằng luật cố định; việc so sánh bốn shape chưa tách riêng mọi ảnh hưởng của topology, prompt và số lần gọi model. Chi phí là mô phỏng; latency là `unavailable`.

Chưa có dữ liệu `student_drop/` để tự kiểm và chưa có kết quả hidden từ giảng viên. Do đó chưa khẳng định đạt ngưỡng hidden 0,75 hoặc các safety count của bộ hidden. Nhóm cần cập nhật kết luận nếu đánh giá chính thức cho kết quả khác.
