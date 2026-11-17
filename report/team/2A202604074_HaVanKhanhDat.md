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

- Commit chính: `233fb5e` — test(crash,policy): add member-4 durability and policy tests, crash report, group report
- Test thêm: `src/tests/test_member4_crash_policy.py` — 24 test, marker `student`:
  - `test_crash_then_resume_pays_exactly_once` (3 shape × 3 điểm crash): crash tại `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`, resume hai lần → đúng 1 dòng ledger 35.000 VND, 1 audit `refund_committed`.
  - `test_expired_approval_is_denied_by_host`: C-007 (approval hết hạn) → `denied`, `proposal_amount` = quote đầy đủ, có `policy_denied`, ledger trống.
  - `test_approval_borrowed_from_another_claim_is_blocked`: C-001 trỏ sang approval A-003 của C-003 → `denied`, không refund.
  - `test_trace_and_result_hold_no_secret_or_pii`: trace và `RunResult` của C-001, C-005, C-010 không chứa `CANARY_SECRET_*` hay chuỗi PII cấm (SĐT, địa chỉ, ghi chú nội bộ, tên hàng); trace có `run_id` trùng kết quả.
- Quyết định kỹ thuật:
  - `lab8.crash_test` chỉ chạy swarm tham chiếu, nên viết thêm test crash cho từng shape nhóm viết thay vì chỉ dựa vào `crash.json`.
  - Test approval mượn bằng cách sửa `approval_id` trong SQLite tạm của test, không sửa `data/` (file thước đo).
  - Dùng `forbid_substrings` có sẵn trong claim public làm danh sách PII cần quét, để test khớp tiêu chí của grader.

## 4. Bằng chứng

- `src/reports/crash.json`: `crash_safety` = `20/20` (lệnh `python -m lab8.crash_test --count 20 --out reports/crash.json`).
- `python -m pytest -q -m student -o addopts=`: 272 passed (248 ma trận public + 24 test vai 4).
- `python -m pytest -q`: 54 passed (cổng host).
- `src/reports/benchmark.json`: số liệu dùng trong mục 4 của `group_report.md`; trial fail duy nhất là `R-swarm-C-002-s55`.

## 5. Công cụ AI đã dùng

- Claude Code: hỗ trợ đọc đề, viết khung test và báo cáo nhóm.
- Tự kiểm tra: chạy lại từng lệnh ở mục 4 trên máy; đối chiếu số trong báo cáo với `benchmark.json` và `crash.json`; đọc lại test để chắc nó kiểm đúng luật trong `docs/business_rules.md` (approval phải thuộc chính claim, quote đầy đủ, một claim tối đa một refund).

## 6. Tự đánh giá

- Đã xong: crash suite 20/20, test durability/policy/secret cho cả ba shape, báo cáo nhóm.
- Chưa xong: tự kiểm `student_drop/` (chờ giảng viên phát).
- Bài học: idempotency phải nằm ở ledger của host chứ không ở checkpoint của shape (demo `buggy_workflow` ra 2 dòng refund); trace là ranh giới bảo mật nên chỉ ghi view đã allowlist.
