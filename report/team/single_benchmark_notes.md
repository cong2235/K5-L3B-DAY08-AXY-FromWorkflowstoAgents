# Ghi chú benchmark shape single (B)

Ghi chú nội bộ, chưa phải số liệu ADR. ADR cần `reports/benchmark.json` đủ 4 shape.

- Lệnh: `python -m lab8.benchmark --shapes single --cases data/public_claims.jsonl --seeds 11,22,33,44,55`
- Corpus: 12 claim public × 5 seed (11, 22, 33, 44, 55)
- Commit khi đo: b8a557c (sau khi pull orchestrator của thành viên khác; single không đổi)

| Chỉ số | single | orchestrator (tham khảo) |
| --- | --- | --- |
| Pass rate | 1.000 | 1.000 |
| pass^5 | 1.000 | 1.000 |
| Variance | 0.000 | 0.000 |
| Cost/success (VND mô phỏng) | 29.82 | 56.66 |
| Steps trung bình | 3.64 | 5.36 |

## Must-pass (tự kiểm trực tiếp trên single, bộ public)

- Không approval thì không refund: xóa toàn bộ approvals, 0/12 claim bị refund.
- Không lộ secret: 12 claim × 5 seed, quét trace và file `<run_id>*`, 0 lần lộ.
- Crash: 12 claim × 3 điểm crash rồi resume và gọi lại, không lượt nào vượt 1 refund / 1 audit `refund_committed`.

## Giới hạn

- Chỉ đo trên bộ public, chưa có hidden. Cost là mô phỏng, latency không có.
- `lab8.crash_test` (20/20) chủ yếu kiểm host, không riêng single.
- pytest trên máy này lỗi môi trường (package `tests` của anaconda đè `src/tests`), nên ma trận student chưa chạy.
