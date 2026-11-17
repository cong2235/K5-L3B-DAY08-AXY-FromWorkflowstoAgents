# Báo cáo cá nhân — Lab 8 LogiX-VN

## 1. Thông tin thành viên

- Họ tên: Nguyễn Đức Khương Lam
- MSSV: 2A202604020
- Email: khuonglam.ai@gmail.com
- GitHub: RachalHys
- Vai trò: Workflow và integration.

## 2. Phần việc phụ trách

Phần việc chính là triển khai Workflow, kiểm tra tính đúng của luồng hoàn tiền và tích hợp với Single, Orchestrator của các thành viên. Sau khi ba shape được ghép vào `main`, tôi phụ trách chạy benchmark, đối chiếu kết quả, hoàn thiện ADR và bổ sung thí nghiệm ablation cho CP5.

## 3. Đóng góp cụ thể

### Workflow và kiểm thử

[Workflow](../../src/lab8/shapes/workflow.py) xử lý claim theo thứ tự cố định: đọc claim, kiểm order và quyền sở hữu, tính quote rồi gọi host khi quote lớn hơn 0. Tiền được tính từ order và policy hiện hành; nội dung ticket không tham gia quyết định số tiền. Workflow không gọi model vì task hiện tại đã có đủ luật xác định bằng code.

Một quyết định quan trọng là truyền quote đầy đủ vào host. Với T14, quyền lợi là 150.000 VND, đơn đã được hoàn 30.000 VND; shape vẫn truyền 150.000 để host chỉ ghi thêm 120.000. Nếu shape tự trừ trước, số tiền sẽ bị trừ hai lần. Các nhánh thiếu thông tin, sai chủ sở hữu, bị từ chối và conflict được trả về đúng contract qua `finish()`.

Workflow truyền `crash_at` xuống host và để crash truyền ra ngoài, đồng thời đóng connection trong `finally`. Trace chỉ ghi dữ kiện cần cho việc kiểm tra, không chứa ticket hay row thô. Trace được lưu trước lời gọi host để vẫn có bằng chứng khi crash xảy ra.

[Test bổ sung](../../src/tests/test_workflow.py) gồm 27 trường hợp: nhánh kết thúc sớm và trace cũ, năm loại approval không hợp lệ, ba cửa sổ crash trên hai claim, conflict khi retry, ticket injection trên năm seed và policy tương lai. Các test được chạy trên stub trước khi triển khai, đều fail vì chức năng chưa có; sau triển khai đều pass.

Trong lần rà soát tiếp theo, tôi bổ sung đối chiếu ledger cho test injection. Trước đó, một biến thể thử nghiệm ghi sai tiền nhưng giữ đúng status và quote vẫn lọt qua nhóm test này. Sau khi siết kiểm tra, test phát hiện đúng lỗi `refund_mismatch`. Năm biến thể sai có chủ đích đều bị test phát hiện; các biến thể chỉ chạy trong bộ nhớ.

### Integration và CP5

Tôi cập nhật các commit của nhóm bằng fast-forward, kiểm tra bản ghép và giữ nguyên code, báo cáo của người phụ trách từng phần. Benchmark được chạy trên cùng 14 claim, năm seed, bảng giá và evaluator; mỗi trial dùng SQLite mới. Một lần chạy độc lập tái lập đúng toàn bộ metric và 280 dòng trial.

Từ số liệu này, [ADR](decision_adr.md) chọn Workflow vì đạt cùng tỷ lệ đúng với Single và Orchestrator nhưng có chi phí thấp nhất. Tôi cũng bổ sung [ablation](research_card.md): chỉ tắt việc Swarm dùng ngày trễ từ ticket, giữ nguyên model và các điều kiện còn lại. Kết quả sửa đúng một trial đã biết mà không tăng số model call. Các số liệu không còn khớp trong báo cáo nhóm được cập nhật theo report mới.

## 4. Bằng chứng và kết quả

| Nội dung | Kết quả |
| --- | --- |
| Ma trận Workflow của đề | 62/62 test pass, gồm retry T11 và crash/resume T12 |
| Test Workflow bổ sung | 27/27 pass |
| Cổng host sau tích hợp và bổ sung ablation | 93 test pass |
| Bộ student của nhóm | 272 test pass |
| Smoke và crash suite | Smoke pass; crash safety 20/20 |
| Benchmark Workflow | 70/70 trial; pass^5 100%; variance 0; cost/success 27,86 VND mô phỏng |
| Ablation Swarm | Từ 69/70 lên 70/70 trial; model calls giữ ở 3/trial |

Code và test Workflow được ghi trong commit `4ee050a`; benchmark và ablation trong commit `4db00d5`. Bằng chứng có thể tra tại [benchmark](../../src/reports/benchmark.json), [crash report](../../src/reports/crash.json) và [ablation report](../../src/reports/research_ablation.json). Run id tiêu biểu là `R-workflow-C-001-s11`; trial lỗi đối chứng là `R-swarm-C-002-s55`.

Các lệnh kiểm tra được chạy trong `src/`: `python -m pytest -q`, `python -m pytest -q -m student -o addopts=`, `python -m lab8.smoke`. Lệnh benchmark và điều kiện đo được ghi trong báo cáo nhóm để chạy lại.

## 5. Công cụ AI đã dùng

Tôi sử dụng Codex để hỗ trợ đọc yêu cầu, triển khai Workflow, viết test, rà diff và soạn báo cáo. Kết quả được kiểm chứng bằng các lệnh kiểm thử, đối chiếu ledger và trace, thử biến thể sai trong bộ nhớ và chạy lại benchmark. Số liệu trong báo cáo lấy từ các lần chạy thực tế, không dùng số do AI tự ước lượng.

## 6. Tự đánh giá

Phần Workflow và các kiểm tra local đã hoàn thành. Điểm cần chú ý nhất là phân biệt quote với khoản tiền host thực ghi, và phân biệt test trả đúng status với test xác nhận đúng tác động trong ledger. Việc phát hiện khoảng trống ở test injection cho thấy test xanh vẫn cần được rà về chất lượng kiểm chứng.

Lựa chọn Workflow phù hợp với task có luật rõ ràng trong bộ public. Kết quả chưa đủ để kết luận về model thật hoặc dữ liệu ngoài tập đã đo. Chưa có dữ liệu `student_drop/` để tự kiểm; kết quả hidden chính thức và các safety count vẫn cần được giảng viên xác nhận.
