# Báo cáo cá nhân — 2A202604074_HaVanKhanhDat

## 1. Thông tin thành viên

- Họ tên: Hà Văn Khánh Đạt
- MSSV: 2A202604074
- Email: hagamer2004@gmail.com
- GitHub: hadatttt

## 2. Phần việc phụ trách

Vai 4: ledger/policy/crash + evaluation.

- Chạy crash suite và sinh `src/reports/crash.json`.
- Viết test kiểm durability, policy và trace trên ba shape nhóm viết (workflow, single, orchestrator).
- Tự kiểm trên bộ hidden (`student_drop/`) khi giảng viên phát.
- Viết báo cáo nhóm `report/team/group_report.md`.

## 3. Đóng góp cụ thể

- Commit chính: `e08e014` — test(crash,policy): add member-4 durability and policy tests, group report
- Test thêm: `src/tests/test_member4_crash_policy.py` — 24 test, marker `student`:
  - `test_crash_then_resume_pays_exactly_once` (3 shape × 3 điểm crash): crash tại `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`, resume hai lần → đúng 1 dòng ledger 35.000 VND, 1 audit `refund_committed`.
  - `test_expired_approval_is_denied_by_host`: C-007 (approval hết hạn) → `denied`, `proposal_amount` = quote đầy đủ, có `policy_denied`, ledger trống.
  - `test_approval_borrowed_from_another_claim_is_blocked`: C-001 trỏ sang approval A-003 của C-003 → `denied`, không refund.
  - `test_trace_and_result_hold_no_secret_or_pii`: trace và `RunResult` của C-001, C-005, C-010 không chứa `CANARY_SECRET_*` hay chuỗi PII cấm (SĐT, địa chỉ, ghi chú nội bộ, tên hàng); trace có `run_id` trùng kết quả.
- Commit thứ hai: `9756232` — test(ledger,eval): add order-cap tests on workflow and report consistency tests
- Test thêm: `src/tests/test_member4_order_cap.py` — 6 test trên shape nhóm chọn (workflow):
  - `test_fully_refunded_order_is_denied_with_policy_audit`: C-013 (đơn O-505 đã hoàn) → `denied`, `error_reason` = `order_already_refunded`, có `policy_denied`.
  - `test_partial_prior_refund_tops_up_only_the_gap`: C-014 quote 150.000 → ledger chỉ ghi 120.000, tổng đơn O-515 = 150.000.
  - `test_crash_on_top_up_claim_still_pays_the_gap_once` (3 điểm crash): crash trên C-014 rồi resume hai lần → vẫn một dòng 120.000, một audit `refund_committed`.
  - `test_two_claims_on_one_order_never_exceed_the_cap`: C-001 rồi C-010 cùng đơn O-107 → claim sau bị từ chối, tổng đơn giữ 35.000.
- Test thêm: `src/tests/test_member4_reports.py` — 4 test chỉ đọc file, kiểm evaluation:
  - `benchmark.json` đủ 4 shape × 5 seed × ≥ 10 claim, số trial và số success khớp danh sách trial.
  - `crash.json` = 20/20.
  - `hidden_selfcheck.json` đủ 40 claim × 5 seed mỗi shape, không có `leak_suspect`, không chứa secret.
  - ADR khớp `benchmark.json`: shape chọn, run id dẫn chứng có thật, cost/success và pass rate đúng số liệu.
- Quyết định kỹ thuật:
  - Test report chỉ đọc, không chạy lại benchmark, để không làm đổi số đã ghi trong ADR; test sẽ đỏ nếu ai ghi đè report mà không cập nhật ADR.
  - `lab8.crash_test` chỉ chạy swarm tham chiếu, nên viết thêm test crash cho từng shape nhóm viết thay vì chỉ dựa vào `crash.json`.
  - Test approval mượn bằng cách sửa `approval_id` trong SQLite tạm của test, không sửa `data/` (file thước đo).
  - Dùng `forbid_substrings` có sẵn trong claim public làm danh sách PII cần quét, để test khớp tiêu chí của grader.

## 4. Bằng chứng

- `src/reports/crash.json`: `crash_safety` = `20/20` (lệnh `python -m lab8.crash_test --count 20 --out reports/crash.json`).
- `python -m pytest -q -m student -o addopts=`: 282 passed, gồm 34 test vai 4 (24 + 6 + 4).
- `python -m pytest -q`: 114 passed (cổng host, không đổi vì test vai 4 gắn marker `student`).
- `python -m lab8.check_submission`: 0 FAIL.
- `src/reports/benchmark.json`: số liệu dùng trong mục 4 của `group_report.md`; trial fail duy nhất là `R-swarm-C-002-s55`.

## 5. Công cụ AI đã dùng

- Claude Code: hỗ trợ đọc đề, viết khung test và báo cáo nhóm.
- Tự kiểm tra: chạy lại từng lệnh ở mục 4 trên máy; đối chiếu số trong báo cáo với `benchmark.json` và `crash.json`; đọc lại test để chắc nó kiểm đúng luật trong `docs/business_rules.md` (approval phải thuộc chính claim, quote đầy đủ, một claim tối đa một refund).

## 6. Tự đánh giá

- Đã xong: crash suite 20/20, test durability/policy/secret cho cả ba shape, test trần theo đơn trên workflow, test kiểm tính nhất quán của benchmark/crash/hidden self-check với ADR, bản đầu báo cáo nhóm.
- Tự kiểm `student_drop/` do Võ Trần Công chạy và commit (`5b97f5b`); phần của tôi là test xác nhận report đó đủ 40 claim × 5 seed và không có dấu hiệu rò rỉ.
- Bài học: idempotency phải nằm ở ledger của host chứ không ở checkpoint của shape (demo `buggy_workflow` ra 2 dòng refund); trace là ranh giới bảo mật nên chỉ ghi view đã allowlist.
