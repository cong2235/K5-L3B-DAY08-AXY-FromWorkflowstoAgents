# Báo cáo cá nhân — Lab 8 LogiX-VN

## 1. Thông tin thành viên

- Họ tên: Nguyễn Đức Khương Lam
- MSSV: 2A202604020
- Email: khuonglam.ai@gmail.com
- GitHub: RachalHys
- Nhóm/lớp: AXY — L3B
- Vai trò: Workflow và integration.

## 2. Phần việc phụ trách

Tôi phụ trách triển khai Workflow, bổ sung test và tích hợp với Single, Orchestrator của các thành viên. Ở CP5, công việc gồm chạy benchmark, đối chiếu số liệu, hoàn thiện ADR và thực hiện ablation cho research card.

## 3. Đóng góp cụ thể

### Workflow và kiểm thử

[Workflow](../../src/lab8/shapes/workflow.py) xử lý claim theo thứ tự cố định: đọc claim, kiểm quyền sở hữu đơn, tính quote và chỉ gọi host khi quote lớn hơn 0. Số tiền được tính từ order và policy hiện hành; lời khai trong ticket không thay thế dữ kiện của đơn hàng. Với quy trình có luật rõ ràng này, Workflow không cần gọi model.

Shape truyền quote đầy đủ để host kiểm approval và trừ khoản đã hoàn trước đó. Ví dụ T14 có quyền lợi 150.000 VND, đã hoàn 30.000 VND; host chỉ ghi thêm 120.000 VND. Shape cũng chuyển tiếp yêu cầu giả lập crash và để ngoại lệ truyền ra ngoài, đồng thời ghi trace an toàn.

Tôi bổ sung [27 trường hợp kiểm thử](../../src/tests/test_workflow.py) cho các nhánh kết thúc sớm, approval, retry/crash, conflict, ticket injection, policy tương lai và trace cũ. Test đối chiếu kết quả trả về với ledger và audit, giúp phát hiện trường hợp status đúng nhưng tác động hoàn tiền sai.

### Integration và CP5

Tôi ghép các phần việc của nhóm và kiểm tra lại bản tích hợp. Benchmark sử dụng cùng dữ liệu, seed, bảng giá và evaluator; mỗi trial dùng database SQLite riêng. Kết quả đã được chạy lại độc lập để kiểm tra khả năng tái lập.

Từ số liệu đo được, tôi hoàn thiện [ADR](decision_adr.md) chọn Workflow vì đạt cùng tỷ lệ đúng với Single và Orchestrator nhưng có chi phí thấp nhất. Thí nghiệm [ablation](research_card.md) kiểm chứng ảnh hưởng của việc Swarm dùng ngày trễ trong ticket. Tôi cũng đối chiếu và cập nhật các số liệu chưa khớp trong báo cáo nhóm.

### Bonus B5

Ở B5, tôi bổ sung provider giả lập lưu dữ liệu trong SQLite riêng. Luồng hoàn tiền lưu reservation trước khi gọi provider, sau đó confirm qua host. Tôi viết job đối soát và test crash để kiểm tra khoản hoàn ở cả provider lẫn ledger, đồng thời dựng phản ví dụ provider không dedupe. Chi tiết có trong [bộ test B5](../../src/tests/test_bonus_provider.py) và [báo cáo bonus](bonus_report.md).

## 4. Bằng chứng và kết quả

| Nội dung | Kết quả |
| --- | --- |
| Workflow | 62 test của đề và 27 test bổ sung đều đạt |
| Cổng host của bản tích hợp | 179 test đạt, gồm 65 test B5 |
| Bộ student của nhóm | 282 test đạt |
| Smoke và crash suite | Smoke đạt; crash safety 20/20 |
| Benchmark Workflow | 70/70 trial; chi phí/success 27,86 VND mô phỏng |
| Ablation Swarm | Từ 69/70 lên 70/70 trial, không tăng số model call |
| Bonus B5 | Provider dedupe đạt 120/120 phiên crash/phục hồi; có phản ví dụ không dedupe |

Commit chính: `4ee050a` cho Workflow và test; `4db00d5` cho benchmark và ablation. Kết quả và lệnh tái lập được tổng hợp trong [báo cáo nhóm](group_report.md).

## 5. Công cụ AI đã dùng

Tôi sử dụng Codex để hỗ trợ đọc yêu cầu, viết code/test và soạn báo cáo. Kết quả được kiểm chứng bằng test, đối chiếu ledger và trace, cùng các lần chạy benchmark thực tế.

## 6. Tự đánh giá

Phần Workflow và kiểm tra tích hợp trên dữ liệu public đã hoàn thành. Bài học chính là phân biệt quote với số tiền thực ghi, đồng thời kiểm tra tác động trong ledger thay vì chỉ dựa vào status trả về.

Với provider bên ngoài, tôi cần đối chiếu cả giao dịch đã thực hiện: một dòng ledger chưa chứng minh tiền chỉ được hoàn một lần.

Nhóm đã tự kiểm bộ hidden không nhãn, chưa ghi nhận lỗi chạy hoặc dấu hiệu rò rỉ. Do chưa có nhãn và kết quả chấm chính thức, chưa thể kết luận về pass rate hidden hay độ ổn định của model thật.
