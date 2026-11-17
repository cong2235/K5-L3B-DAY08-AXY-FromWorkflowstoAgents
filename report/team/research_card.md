# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R2 — Failure taxonomy. Kiểm chứng nguyên nhân Swarm sai ở seed 55. |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Cemri và cộng sự, [Why Do Multi-Agent LLM Systems Fail?](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html), NeurIPS 2025. Nghiên cứu thực nghiệm và phân loại trace. |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | MAST xác định 14 dạng lỗi, chia thành ba nhóm: thiết kế hệ thống, lệch mục tiêu giữa agent và kiểm chứng tác vụ. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Nghiên cứu dùng hơn 1.600 trace từ bảy framework MAS. LogiX với 14 claim và MockLLM là bối cảnh khác; thí nghiệm này không tái lập toàn bộ nghiên cứu. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Tắt việc dùng ngày trễ từ ticket trong Swarm sẽ sửa C-002 ở seed 55: pass rate từ 69/70 lên 70/70, pass^5 từ 13/14 lên 14/14; số model call giữ nguyên. Giả thuyết dựa trên điểm yếu đã công bố trong starter. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ nguyên Swarm, MockLLM, tập tool, host, 14 claim, năm seed, giá và evaluator. Chỉ thay giá trị ngày trễ trích từ ticket thành `None` trong phạm vi test; không sửa file shape. Lời gọi MockLLM parse vẫn chạy. Mỗi trial dùng SQLite mới. |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: lời khai trong ticket ghi đè dữ kiện order. Nhóm diễn giải đây là lỗi kiểm chứng tác vụ, không phải nhãn do tác giả paper gán cho LogiX. Đo pass rate, pass^5, variance, cost/success, model calls và trial thay đổi. |

## Kết quả ablation

- Lệnh đã chạy trong `src/`: `python -m pytest -q tests/test_research_ablation.py`.
- File report: [research_ablation.json](../../src/reports/research_ablation.json), do test sinh. Baseline trùng số liệu Swarm trong [benchmark](../../src/reports/benchmark.json).
- Run id: `R-swarm-C-002-s55`, phân biệt theo hai nhánh `baseline` và `ablated` trong report.

| Chỉ số | Swarm gốc | Tắt ngày trễ từ ticket |
| --- | ---: | ---: |
| Trial pass | 69/70 | 70/70 |
| Pass rate | 98,57% | 100% |
| Pass^5 | 92,86% | 100% |
| Seed min–max | 92,86–100% | 100–100% |
| Variance | 0,000816 | 0 |
| Cost/success, VND mô phỏng | 49,57 | 48,72 |
| Model calls/trial | 3 | 3 |

Kết quả ủng hộ giả thuyết trên bộ public: chỉ C-002 ở seed 55 đổi từ sai sang đúng; 69 trial còn lại giữ nguyên toàn bộ số đo. Vì vậy lỗi quan sát được gắn với việc sử dụng dữ kiện từ ticket, không cần thay topology hoặc giảm số model call để sửa trial này.

Thí nghiệm chỉ kiểm chứng một lỗi đã biết của starter. Nó không chứng minh hiệu quả của một verifier tổng quát, độ tin cậy trên hidden hay khả năng suy luận của model thật. MockLLM là giới hạn bắt buộc; latency là `unavailable`. Đây là ablation cho CP5, không phải bài bonus.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
