# Team

## Thông tin nhóm

- Tên nhóm: AXY
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-AXY-FromWorkflowstoAgents`
- URL repo, nhánh nộp, commit chốt: [GitHub](https://github.com/cong2235/K5-L3B-DAY08-AXY-FromWorkflowstoAgents), `main`; commit tham chiếu trong [ADR](report/team/decision_adr.md).

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 |        Võ Trần Công|    2A202604026  | congvotran2003@gmail.com |        cong2235|        Trưởng nhóm |
|   2 |        Nguyễn Đức Khương Lam    |      2A202604020| khuonglam.ai@gmail.com |        RachalHys|Thành viên         |
|   3 |        Từ Huy Bảo|    2A202604021  | thbao552003@gmail.com |        thbao4545|        Thành viên |
|   4|       Hà Văn Khánh Đạt  |      2A202604074| hagamer2004@gmail.com |        hadatttt|         Thành viên|

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Võ Trần Công | single | `983d506`, `14188e7` | `src/tests/test_single_extra.py` |
| Từ Huy Bảo | orchestrator + handoff | `6200002`, `b8a557c` | `src/tests/test_orchestrator_extra.py` |
| Nguyễn Đức Khương Lam | Workflow + integration | `4ee050a`, `4db00d5` | `src/tests/test_workflow.py`, `src/tests/test_research_ablation.py` |
| Hà Văn Khánh Đạt| ledger + evaluation| `e08e014`, `9756232` | `src/tests/test_member4_crash_policy.py`, `src/tests/test_member4_order_cap.py`, `src/tests/test_member4_reports.py` |



## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202604026_VoTranCong

### Phần việc phụ trách

- Trưởng nhóm. Cài shape B (single): agent ReAct tối đa 8 bước, model chỉ chọn tool đọc, host là bên duy nhất ghi refund.

### Đóng góp cụ thể

- Commit `983d506`: cài `src/lab8/shapes/single.py`. Commit `14188e7`: thêm test cho single.
- Test `src/tests/test_single_extra.py` (21 test): `needs_info`, `escalated`, claim không tồn tại, ticket "ignore policy", gọi lại cùng claim, trần theo đơn T13 và T14, trần 8 bước và trace sạch.
- Chạy benchmark và tự kiểm must-pass (approval, secret, crash) trên single.

### Bằng chứng

- `src/reports/benchmark.json`: single pass 1.000, pass^5 1.000, cost/success 29.82 VND mô phỏng, 3.64 bước (14 claim × 5 seed).
- Báo cáo đầy đủ: [report/team/2A202604026_VoTranCong.md](report/team/2A202604026_VoTranCong.md).

-
