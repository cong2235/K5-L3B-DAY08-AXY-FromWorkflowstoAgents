# Decision record

- Shape chọn: workflow
- Commit hash: 5b97f5b
- Run id dẫn chứng: `R-workflow-C-001-s11`, xem [benchmark](../../src/reports/benchmark.json).
- Pass rate / pass^5 / seed min-max / variance: 100% / 100% / 100–100% / 0, trên bộ public 14 claim × 5 seed.
- Cost per success (mô phỏng, VND): 27,86.
- Crash safety: 20/20 theo [crash report](../../src/reports/crash.json), kịch bản `CR-01`–`CR-20`; có test crash riêng cho Workflow.
- Secret leak / approval bypass: Không phát hiện trong các kiểm tra public/local; chưa có kết quả hidden chính thức.

## Vì sao shape này

Workflow, Single và Orchestrator đều đạt 70/70 trial trên cùng dữ liệu và năm seed. Workflow có chi phí/success thấp nhất: 27,86 VND mô phỏng, so với 29,82 của Single và 56,66 của Orchestrator. Quy trình xét claim có thứ tự và luật rõ ràng nên chưa cần tăng mức tự chủ.

Swarm đạt 69/70 trial. Lỗi xảy ra khi shape dùng ngày trễ trong ticket thay cho order; nguyên nhân được kiểm chứng trong [research card](research_card.md).

## Có đáng đổi lấy multi-agent không

Trên tập đã đo, Single và Orchestrator chưa cải thiện tỷ lệ đúng so với Workflow, trong khi chi phí cao hơn. Nhóm chọn Workflow để giữ cách xử lý đơn giản và ranh giới trách nhiệm rõ ràng.

Cần xem lại quyết định nếu dữ liệu mới có claim cần suy luận văn bản tự do mà Workflow không xử lý được, hoặc khi kiến trúc khác tăng tỷ lệ đúng đủ để bù chi phí. Khi đó phải đo lại trong cùng điều kiện.

## Trace và bằng chứng

Trace ghi các bước tra claim/order, quote, yêu cầu refund, kết quả host và quyết định cuối. Không ghi ticket, dữ liệu thô, secret, header, SĐT, địa chỉ, ghi chú nội bộ hoặc tên hàng; không có log ngoài phạm vi quét của grader.

[Benchmark](../../src/reports/benchmark.json) gồm 280 trial, mỗi shape có 70 trial. Benchmark và [crash report](../../src/reports/crash.json) được công cụ sinh. Benchmark đã được chạy lại độc lập và cho kết quả khớp dữ liệu lưu trong report. Ngoài suite chung kiểm host và Swarm, test riêng xác nhận Workflow không hoàn trùng khi crash/resume.

## Giới hạn

Kết luận dựa trên 14 claim public và MockLLM. So sánh hiện tại chưa tách riêng mọi ảnh hưởng của topology, prompt và số lần gọi model. Chi phí là mô phỏng; latency là `unavailable`, không suy ra từ số event trace.

Tự kiểm [student_drop](../../src/reports/hidden_selfcheck.json) trên 40 claim × 5 seed cho mỗi shape không ghi nhận lỗi chạy hoặc dấu hiệu rò rỉ. Bộ dữ liệu không có nhãn nên chưa thể khẳng định đạt ngưỡng hidden 0,75 và các yêu cầu an toàn chính thức.
