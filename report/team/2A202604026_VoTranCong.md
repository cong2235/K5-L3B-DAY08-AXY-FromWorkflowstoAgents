# Báo cáo cá nhân — 2A202604026_VoTranCong

## 1. Thông tin thành viên

- Họ tên: Võ Trần Công
- MSSV: 2A202604026
- Email: congvotran2003@gmail.com
- GitHub: cong2235

## 2. Phần việc phụ trách

Trưởng nhóm, phụ trách shape B (single): một agent ReAct có giới hạn trong `src/lab8/shapes/single.py`.

- Cài shape single: model chỉ chọn tool đọc, host là bên duy nhất ghi refund.
- Chạy benchmark riêng cho single và tự kiểm ba điều kiện must-pass trên shape này.
- Viết test bổ sung cho single.
- Điều phối nhóm: chia vai, theo dõi checkpoint, gom commit của các thành viên.

## 3. Đóng góp cụ thể

- Commit chính: `983d506` — feat(single): implement shape B as a bounded ReAct agent. Commit test: `14188e7`.
- Test thêm: `src/tests/test_single_extra.py` — 21 test:
  - `test_missing_order_id_needs_info_and_writes_nothing` (C-004): `needs_info`, ledger trống.
  - `test_foreign_principal_is_escalated_without_ledger` (C-005): `escalated`, không ghi ledger.
  - `test_unknown_claim_fails_without_raising`: claim không tồn tại trả `failed`, không ném exception.
  - `test_ticket_text_cannot_force_a_refund` (C-009 "ignore policy"): `denied`, quote 0.
  - `test_paying_claim_commits_exactly_once_on_replay` (C-001): gọi hai lần, một dòng ledger 35.000, một audit `refund_committed`.
  - `test_order_cap_uses_full_quote_and_pays_only_the_difference` (T14, C-014): `proposal_amount` 150.000, ledger 120.000.
  - `test_already_refunded_order_is_denied_with_audit` (T13, C-013): `denied`, `proposal_amount` 35.000, có `policy_denied`.
  - `test_react_loop_stays_within_step_cap_and_trace_matches_run` (14 claim): số bước không vượt trần, trace có `run_id` trùng kết quả, không chứa `CANARY_SECRET_` hay `parent_secret`.
- Quyết định kỹ thuật:
  - Số ngày trễ lấy từ order row, không lấy từ ticket. Ticket không đi vào observation của vòng ReAct và không vào trace.
  - Shape truyền quote đầy đủ vào `durability.issue_refund` và không tự trừ phần đã hoàn. Host trừ, nên T14 ra 120.000.
  - `InjectedCrash` chỉ được bắt để ghi trace rồi ném lại, nên T12 thấy crash thật.
  - Quote bằng 0 thì không gọi `issue_refund`. Quote lớn hơn 0 mà host từ chối thì vẫn gọi `issue_refund` để host ghi audit `policy_denied`.
  - Giữ `MAX_STEPS = 8` và cộng mọi lần gọi model và tool vào `Budget`, để cost so sánh được với các shape khác.

## 4. Bằng chứng

- `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` (14 claim × 5 seed). Dòng single: pass 1.000, pass^5 1.000, variance 0, cost/success 29.82 VND mô phỏng, trung bình 3.64 bước. Run id ví dụ: `R-single-C-001-s11`.
- `python -m pytest -q tests/test_single_extra.py -o addopts=`: 21 passed.
- `python -m lab8.check_submission`: `shape single: format đúng`, `reports/benchmark.json: 4 shape x 14 claim x 5 seed`.
- Tự kiểm must-pass trên shape single (bộ public, script chạy ngoài repo):
  - Xóa toàn bộ approvals: 0 trên 12 claim bị refund (`approval_bypass` = 0).
  - 12 claim × 5 seed, quét trace và file `<run_id>*`: 0 lần lộ `CANARY_*`.
  - 12 claim × 3 điểm crash rồi resume và gọi lại: không lượt nào vượt một refund hay một audit `refund_committed`.
- Ghi chú đo: `report/team/single_benchmark_notes.md`.

## 5. Công cụ AI đã dùng

- Claude Code: đọc tài liệu và code, giải thích rubric, chạy benchmark, viết khung test và bản nháp báo cáo này.
- Tự kiểm tra: chạy lại benchmark và test trên máy; đối chiếu số trong báo cáo với `src/reports/benchmark.json`; đọc lại `single.py` và `durability.py` để chắc test kiểm đúng luật trong `docs/business_rules.md` (quote đầy đủ, một claim tối đa một refund, approval đúng claim).

## 6. Tự đánh giá

- Đã xong: shape single qua bộ public ở cả 5 seed, 21 test bổ sung, kiểm must-pass trên single.
- Chưa xong:
  - Chưa chạy được ma trận student `pytest -m student` trên máy này vì package `tests` của anaconda đè `src/tests`. Test mới được chạy riêng từng file.
  - Chưa có pass rate hidden vì `student_drop/` không có nhãn. Tự kiểm đã chạy: single 200 trial (40 claim × 5 seed), 0 lỗi, 0 `leak_suspect`, `status` ổn định giữa các seed và trùng với workflow và orchestrator (`src/reports/hidden_selfcheck.json`).
- Hạn chế của shape: `decide()` đi theo chuỗi lookup, compute, final khá cố định, nên model gần như không có quyền tự chủ. Single chưa tự hỏi thêm khi ticket mơ hồ và chưa gọi `lookup_refund_history`.
- Bài học: cách an toàn nhất để chỉ hoàn một lần là để host giữ ledger, idempotency và trần theo đơn, còn shape chỉ đề xuất quote. Trace là ranh giới bảo mật nên chỉ ghi dữ liệu đã qua allowlist.
