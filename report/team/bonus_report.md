# Bonus report: B5

- **Topic và nguồn:** Provider idempotency và reconciliation. DBOS, [Durable Execution](https://www.dbos.dev/durable-execution), tài liệu không ghi năm; N8, slide 36–37.
- **CLAIM:** Checkpoint giúp tiếp tục công việc sau crash; để retry không hoàn tiền hai lần, provider cần nhận biết idempotency key.
- **BOUNDARY:** Bảo đảm phụ thuộc provider lưu và xử lý key. Bài thử dùng hai database SQLite độc lập, với lịch sử truy vấn đầy đủ.
- **HYPOTHESIS:** Provider có dedupe chỉ hoàn một lần sau crash/retry. Khi không có dedupe, đối soát trước khi gửi lại sẽ tránh hoàn trùng trong luồng phục hồi tuần tự.
- **Biến cố định/thay đổi:** Giữ nguyên claim, điểm crash, seed, luật và giá; thay khả năng dedupe và cách phục hồi: retry hoặc reconcile. Mỗi phiên dùng hai database mới, cố định provider và chế độ dedupe; mỗi lần refund/lookup tính bằng một tool call của lab.
- **Lệnh tái lập:** Chạy trong `src/` sau khi kích hoạt môi trường:

```text
python -m pytest -q tests/test_bonus_provider.py
python -m bonus.evaluate_provider --out reports/bonus_provider.json
```

- **Bằng chứng:** [Kết quả đánh giá](../../src/reports/bonus_provider.json); phiên `R-dedupe_reconcile-PB-02-s11`.

## Kết quả

Luồng xử lý là reserve → provider.refund → confirm. Reservation được lưu sau khi kiểm approval. Host giữ nguyên transaction ledger và audit `refund_committed`; điểm crash sau confirm nằm trước audit đối soát riêng của bonus.

Bốn trường hợp gồm hoàn ship, hỏng hàng, approval thấp hơn quote và đơn đã hoàn một phần. Mỗi trường hợp được thử tại ba điểm: sau reserve, sau provider và sau confirm trước audit, tạo thành 12 kịch bản. Với năm seed, mỗi phương án có 60 phiên; Pass^5 tính trên từng cặp claim–điểm crash. Phiên đạt phải có đúng một khoản hoàn ở provider và một dòng ledger cho claim, đúng tiền, đủ audit, trace an toàn.

| Provider / phục hồi | Pass rate | Pass^5 | Variance | Cost/success (VND) | Phiên hoàn trùng |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dedupe / retry | 100% | 100% | 0 | 73,33 | 0 |
| Dedupe / reconcile | 100% | 100% | 0 | 50,00 | 0 |
| Không dedupe / retry | 66,7% | 66,7% | 0 | 110,00 | 20 |
| Không dedupe / reconcile | 100% | 100% | 0 | 50,00 | 0 |

Phản ví dụ không dedupe/retry có 20 phiên hoàn hai lần ở provider dù ledger chỉ có một dòng. Cả 50 lượt approval không hợp lệ đều bị chặn; không ghi nhận bypass hay rò rỉ secret/PII.

Chi phí gồm lần crash và phục hồi. Reconcile dùng reservation đã lưu nên bớt tra cứu so với retry từ đầu. Trên 14 claim public × 5 seed, Workflow và bản thêm provider đều đạt 70/70; cost/success lần lượt là 27,86 và 32,86 VND mô phỏng. Workflow gốc chỉ ghi ledger nội bộ.

## Kết luận

Kết quả ủng hộ giả thuyết: sau provider, trước confirm, ledger dedupe một mình không ngăn hoàn trùng bên ngoài. Reconciliation tìm giao dịch đã thực hiện rồi hoàn tất ghi nhận. Trace minh họa cho thấy job dùng receipt cũ để confirm, không gửi refund lần nữa.

Với provider không dedupe, kết quả an toàn chỉ áp dụng khi lookup đầy đủ và phục hồi tuần tự. Lợi ích chi phí có thể mất nếu lookup đắt hơn hoặc retry cũng dùng lại reservation.

## Giới hạn

Crash được giả lập, chưa kiểm mất điện hay lỗi lưu trữ. Các writer cần phối hợp theo đơn; thay đổi approval hoặc số tiền giữa chừng có thể cần xử lý thủ công. Bài chạy trong môi trường MockLLM, nhưng B5 không gọi model nên seed không đo độ dao động LLM thật. Chi phí là mô phỏng, latency không đo. Điều kiện tính điểm bonus còn chờ kết quả hidden chính thức.
