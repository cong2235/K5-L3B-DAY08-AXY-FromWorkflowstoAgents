# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm:
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Bài toán: xử lý claim hoàn phí vận chuyển của LogiX-VN bằng bốn kiến trúc có cùng chữ ký `run_claim`, rồi chọn kiến trúc **ít tự chủ nhất mà vẫn làm được việc** dựa trên số đo.

Nhóm 4 người, chia theo gợi ý trong `TEAM.md`:

1. Workflow (Shape A) + integration, chạy benchmark, chốt ADR.
2. Single agent (Shape B), research card.
3. Orchestrator (Shape C) + handoff, rà trace.
4. Ledger/policy/crash + evaluation: crash suite, test policy/crash, tự kiểm hidden, báo cáo nhóm.

Thứ tự: đọc contract và swarm tham chiếu (CP1) → viết workflow trước làm baseline, rồi single và orchestrator dùng chung các bước host (CP2) → nối `crash_at`, handoff allowlist (CP3) → crash suite và test policy (CP4) → benchmark, ADR (CP5).

## 3. Giải pháp

Nguyên tắc chung cho cả ba shape (xem [docs/architecture.md](../../docs/architecture.md)):

- **Tiền do code quyết:** số tiền luôn từ `compute_compensation` trên dòng order đã qua allowlist. Số ngày trễ hay điều khoản ghi trong ticket bị bỏ qua.
- **Model chỉ đọc và soạn chữ:** MockLLM dùng để soạn câu trả lời (và bước "think" của single); không chọn số tiền, không gọi tool ghi.
- **Host là người ghi duy nhất:** shape gọi `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Host kiểm approval, trần theo đơn, idempotency `refund:{claim_id}`. Shape không tự trừ phần đã hoàn (T13, T14). Không bắt `InjectedCrash`; trước khi để exception đi tiếp thì ghi trace.
- **Trạng thái:** thiếu `order_id` → `needs_info`; order không thấy được (không tồn tại / khác principal) → `escalated`; quote = 0 → `denied` (không gọi host); host từ chối → `denied` (host ghi `policy_denied`); `amount_conflict` → `failed`; thành công → `resolved`.

| Shape | Đọc gì | Ai quyết | Model calls TB |
| --- | --- | --- | ---: |
| A workflow | `get_claim_view` → `lookup_order` → `compute_compensation` theo thứ tự cố định | Code Python | 1.00 |
| B single | Vòng `run_react` tối đa 8 bước; `decide` chỉ chọn `lookup_order`, `compute_compensation` | Model chọn tool đọc; code gọi host sau vòng lặp | 3.71 |
| C orchestrator | Orchestrator đọc claim view, dựng handoff bằng `make_handoff` (allowlist, `facts={}`), investigator chạy `lookup_order`, `lookup_refund_history`, `lookup_policy`, `compute_compensation` qua `run_readonly_investigators` | Orchestrator quote và gọi host; investigator không có tool ghi | 2.93 |

**Handoff:** chỉ chứa field trong `ALLOWED_FIELDS`, tool trong `READONLY_TOOLS`; `sanitize` từ chối nếu còn `CANARY_SECRET_`, `parent_secret`, `raw_headers`. Trace ghi bản handoff đã sanitize, không ghi parent context.

**Trace:** dùng `lab8.trace.Trace`, ghi ở mọi nhánh return. Event: `claim` (chỉ `claim_id`, `found`, `order_id`), `lookup_order` / `observation` (view đã allowlist), `handoff`, `quote`, `issue_refund` / `host` (`ok`, `reason`, `conflict`), `crash`, `decision`. Không ghi ticket, claim row hay order row thô.

## 4. Kết quả

Benchmark bộ public: 14 claim × seed `11,22,33,44,55`, MockLLM, SQLite mới cho mỗi trial, bảng giá `config/pricing.yaml` (VND mô phỏng). Nguồn: `src/reports/benchmark.json`.

| Shape | Pass rate | pass^5 | Seed min–max | Variance | Cost/success (VND) | Mean / p95 steps |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 28.79 | 4.43 / 5 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 29.82 | 3.64 / 4 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 57.57 | 5.36 / 6 |
| swarm | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3 |

- Swarm fail đúng một trial: `R-swarm-C-002-s55` (`status resolved != denied`). Ở seed chia hết cho 5, swarm tin "trễ 5 ngày" trong ticket thay vì `delay_days = 2` trong order, nên trả tiền cho claim đáng lẽ bị từ chối. Ba shape nhóm viết quote từ order row nên không dính.
- Crash suite: `src/reports/crash.json` → `crash_safety` = **20/20**.
- Test vai 4 (`src/tests/test_member4_crash_policy.py`, 24 test, xanh) trên cả ba shape: crash tại `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint` rồi resume → đúng 1 dòng ledger, 1 audit `refund_committed`; approval hết hạn (C-007) → `denied`, có `policy_denied`; approval mượn của claim khác → `denied`, ledger trống; trace và `RunResult` không chứa `CANARY_SECRET_*` hay các chuỗi PII cấm của C-001, C-005, C-010.
- Ma trận student: 248/248 passed; cổng host `python -m pytest -q` xanh.
- Tự kiểm `student_drop/`: chưa chạy (chưa nhận thư mục). Lệnh sẽ chạy: `python -m lab8.benchmark --shapes workflow,single,orchestrator --cases student_drop/hidden_claims.jsonl --world student_drop/hidden_world_state.json --out reports/hidden_selfcheck.json`.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

- **Python 3.14 mặc định trên máy Windows** nằm ngoài khoảng hỗ trợ 3.11–3.13 → tạo venv bằng `py -3.11 -m venv .venv`.
- **`run_react` chỉ đưa cho `decide` kết quả tool cuối cùng** → giữ trạng thái (order view, quote) trong closure bên ngoài vòng lặp.
- **Trùng file khi pull:** hai người cùng viết `single.py`; nhóm giữ bản đã commit của người phụ trách shape B, bản còn lại lưu riêng để đối chiếu. Sau khi pull, chạy lại toàn bộ test: vẫn xanh.
- **Crash suite (`lab8.crash_test`) chỉ chạy swarm** → viết thêm test crash 3 điểm × 3 shape để có bằng chứng cho shape nhóm viết.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

- MockLLM không phải model sản xuất: sinh chữ theo hash của seed + prompt, nên variance 0 của workflow/single/orchestrator phản ánh việc model không được phép quyết định gì, chứ không chứng minh một LLM thật sẽ ổn định như vậy. Latency là `unavailable`; cost là VND mô phỏng, không phải hóa đơn API.
- Bộ public chỉ 14 claim; kết luận "pass 1.000" chưa đủ để khẳng định trên bộ hidden 40 claim (homoglyph, principal lẫn, injection…).
- `decide` của single là luật cố định nên single gần như workflow cộng thêm model call. Nếu cho model tự chọn tool hoặc đọc ticket, cần đo lại variance.
- Điều kiện làm kết luận đổi: nếu hidden có loại claim cần suy luận trên văn bản tự do mà code cố định không xử lý được, kiến trúc có tự chủ (single) có thể đáng thêm chi phí; nếu chi phí model thật cao hơn nhiều, khoảng cách workflow vs orchestrator còn lớn hơn.

## 8. Tài liệu tham khảo

- [docs/business_rules.md](../../docs/business_rules.md), [docs/contracts.md](../../docs/contracts.md), [docs/architecture.md](../../docs/architecture.md), [docs/metrics.md](../../docs/metrics.md)
- `src/reports/benchmark.json`, `src/reports/crash.json`
