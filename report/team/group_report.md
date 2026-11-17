# Báo cáo nhóm — Lab 8 LogiX-VN

## 1. Thông tin nhóm

- Nhóm: AXY — L3B.
- Thành viên và đóng góp: [TEAM.md](../../TEAM.md).

## 2. Mục tiêu và cách tiếp cận

Nhóm xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc có cùng chữ ký `run_claim`, sau đó chọn kiến trúc ít tự chủ nhất vẫn đáp ứng yêu cầu dựa trên kết quả đo.

Công việc được chia thành Workflow và integration; Single; Orchestrator và handoff; ledger, policy, crash và evaluation. Nhóm dùng host, MockLLM và Swarm tham chiếu có sẵn, triển khai ba shape còn lại rồi kiểm tra trên cùng dữ liệu và seed.

## 3. Giải pháp

Số tiền được tính bằng `compute_compensation` từ order và policy hiện hành. Nội dung ticket là lời khai của khách, không được dùng để thay dữ kiện của đơn hàng hay bỏ qua policy.

Với quote lớn hơn 0, shape truyền quote đầy đủ vào `issue_refund`; host kiểm approval, trần theo đơn và idempotency trước khi ghi ledger. Shape không tự trừ phần đã hoàn. Khi giả lập crash, ngoại lệ phải truyền ra ngoài để kiểm tra việc resume.

| Shape | Cách xử lý | Ranh giới trách nhiệm | Model calls TB |
| --- | --- | --- | ---: |
| Workflow | Đọc claim, order và tính quote theo thứ tự cố định | Code quyết định luồng và gọi host | 0 |
| Single | Tra order và tính quote trong vòng ReAct, tối đa 8 bước | Agent chỉ dùng tool đọc; code gọi host | 3,71 |
| Orchestrator | Investigator đọc order, policy và lịch sử refund qua handoff | Investigator chỉ đọc; orchestrator gọi host | 1 |

Thiếu order ID trả `needs_info`; không thấy đơn hoặc sai chủ sở hữu trả `escalated`; không đủ điều kiện hoặc bị host từ chối trả `denied`. Claim không tồn tại hay conflict trả `failed`; host chấp nhận refund trả `resolved`.

Handoff được tạo bằng allowlist, không chuyển parent context hay tool ghi cho investigator. Trace ghi các bước tra cứu, quote, handoff nếu có, kết quả host và quyết định; không ghi ticket, secret hoặc thông tin cá nhân. Các nhánh trả kết quả đều có trace.

## 4. Kết quả

Benchmark dùng 14 claim public, seed `11,22,33,44,55`, cùng MockLLM, bảng giá và evaluator. Mỗi trial dùng SQLite mới. Nguồn số liệu: [benchmark](../../src/reports/benchmark.json).

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean/p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| Workflow | 100% | 100% | 100–100% | 0 | 27,86 | 5,07 / 6 |
| Single | 100% | 100% | 100–100% | 0 | 29,82 | 3,64 / 4 |
| Orchestrator | 100% | 100% | 100–100% | 0 | 56,66 | 5,36 / 6 |
| Swarm | 98,6% | 92,9% | 92,9–100% | 0,0008 | 49,57 | 2,80 / 3 |

Swarm sai một trial ở C-002, seed 55: ticket nói trễ 5 ngày, order ghi 2 ngày. Swarm tin ticket và hoàn tiền cho claim đáng lẽ phải từ chối. Ba shape nhóm viết đều tính quote từ order nên đạt 70/70 trial.

Nhóm chọn Workflow vì đạt cùng tỷ lệ đúng với Single và Orchestrator nhưng có chi phí thấp nhất. Lý do, điều kiện xem lại quyết định và giới hạn được trình bày trong [ADR](decision_adr.md).

Ablation tắt việc Swarm dùng ngày trễ từ ticket đưa kết quả từ 69/70 lên 70/70 trial, không tăng số model call. Chi tiết phương pháp và kết quả nằm trong [research card](research_card.md).

Các kiểm tra trên bản tích hợp:

| Kiểm tra | Kết quả |
| --- | ---: |
| Cổng host, gồm 65 test bonus B5 | 179 test đạt |
| Bộ student | 282 test đạt |
| Crash suite | 20/20 |

Ngoài suite chung kiểm host và Swarm, nhóm có test trực tiếp cho ba shape: crash tại ba cửa sổ rồi resume, approval hết hạn hoặc sai claim, và kiểm tra rò rỉ secret, thông tin cá nhân trong trace và kết quả.

Benchmark đã được chạy lại độc lập và khớp report đã lưu. Các bảng dùng số làm tròn; chi phí là VND mô phỏng. `steps` đếm event trace, không phải latency hay số bước ReAct có thể so trực tiếp giữa mọi shape. Lệnh tái lập nằm ở phụ lục.

Nhóm đã tự kiểm `student_drop/`: 40 claim × 5 seed cho mỗi shape, không ghi nhận lỗi chạy hoặc dấu hiệu rò rỉ. [Report tự kiểm](../../src/reports/hidden_selfcheck.json) không có nhãn nên chưa tính được pass rate hidden.

Ở bonus B5, nhóm mô phỏng hoàn tiền qua provider riêng và phục hồi sau crash. [Báo cáo bonus](bonus_report.md) trình bày cách đối soát giao dịch của provider với ledger và kết quả kiểm tra.

## 5. Khó khăn và cách xử lý

- Máy dùng Python 3.14 nằm ngoài khoảng hỗ trợ của lab; thành viên chuyển sang venv Python 3.11 bằng `py -3.11 -m venv .venv`.
- Vòng ReAct chỉ trả observation cuối cho bước tiếp theo; Single lưu trạng thái cần thiết trong phần điều phối.
- Crash suite chung chưa kiểm trực tiếp ba shape nhóm viết; nhóm bổ sung test crash riêng cho từng shape.
- Một lượt `python -m pytest -q -m student -o addopts=` báo `stale_trace` trên WSL. Bộ test và benchmark chạy lại khớp kết quả đã lưu.

## 6. Tổng hợp đóng góp

Phân công, commit và test của từng thành viên được ghi trong TEAM.md. Báo cáo cá nhân trình bày phần việc, quyết định kỹ thuật và bằng chứng tương ứng.

## 7. Hạn chế và hướng cải thiện

Bộ public chỉ có 14 claim và dùng MockLLM. Variance bằng 0 trong lab không chứng minh model thật sẽ ổn định như vậy. Latency là `unavailable`; chi phí mô phỏng không phải hóa đơn API.

Single hiện chọn tool theo luật khá cố định, nên so sánh giữa các shape chưa tách riêng mọi ảnh hưởng của topology, prompt và số model call. Nếu dữ liệu mới cần suy luận văn bản tự do, nhóm cần đo lại để xác định kiến trúc tự chủ hơn có cải thiện đủ để bù chi phí hay không.

## 8. Tài liệu tham khảo

- [Luật nghiệp vụ](../../docs/business_rules.md), [contract](../../docs/contracts.md), [kiến trúc](../../docs/architecture.md), [metric](../../docs/metrics.md).
- [Benchmark](../../src/reports/benchmark.json), [crash report](../../src/reports/crash.json) và nguồn nghiên cứu trong research card.

## Phụ lục — Lệnh tái lập

Chạy trong `src/` sau khi kích hoạt môi trường:

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json
python -m lab8.crash_test --count 20 --out reports/crash.json
python -m pytest -q tests/test_research_ablation.py
python -m lab8.benchmark --shapes workflow,single,orchestrator --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json --out reports/hidden_selfcheck.json
```
