# Research card

Nhóm chọn R2 để kiểm chứng nguyên nhân Swarm sai ở seed 55 bằng một ablation trên bộ public.

## Phiếu của nhóm

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R2 — Failure taxonomy. |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Cemri và cộng sự, [nghiên cứu MAST](https://arxiv.org/abs/2503.13657), NeurIPS 2025; phân tích trace của các hệ MAS. |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | MAST phân loại 14 dạng lỗi thành ba nhóm: thiết kế hệ thống, lệch mục tiêu giữa agent và kiểm chứng tác vụ. |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Nghiên cứu dùng hơn 1.600 trace từ bảy framework. LogiX chỉ có 14 claim public và MockLLM, nên không đại diện cho toàn bộ bối cảnh của paper. |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Bỏ việc dùng ngày trễ từ ticket sẽ sửa đúng một trial đã biết của Swarm mà không tăng số model call. |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ nguyên Swarm, MockLLM, tập tool, host, dữ liệu, năm seed, giá và evaluator. Chỉ tắt việc dùng ngày trễ từ ticket; các lời gọi model vẫn chạy. Mỗi trial dùng SQLite mới. |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Nhóm diễn giải việc tin ticket hơn order là lỗi kiểm chứng tác vụ. Đo pass rate, pass^5, variance, cost/success và model calls. |

## Kết quả ablation

Chạy trong `src/`: `python -m pytest -q tests/test_research_ablation.py`.

Bằng chứng: [ablation report](../../src/reports/research_ablation.json). Run id `R-swarm-C-002-s55` được đối chiếu giữa hai nhánh `baseline` và `ablated`; baseline khớp số liệu Swarm trong benchmark.

| Chỉ số | Swarm gốc | Tắt ngày trễ từ ticket |
| --- | ---: | ---: |
| Pass rate | 98,6% (69/70) | 100% (70/70) |
| Pass^5 | 92,9% | 100% |
| Seed min–max | 92,9–100% | 100–100% |
| Variance | 0,0008 | 0 |
| Cost/success, VND mô phỏng | 49,57 | 48,72 |
| Model calls/trial | 3 | 3 |

Kết quả ủng hộ giả thuyết: chỉ C-002 ở seed 55 đổi từ sai sang đúng; 69 trial còn lại giữ nguyên số đo. Lỗi quan sát được gắn với việc dùng dữ kiện từ ticket, không cần thay topology hoặc tăng số lần gọi model để sửa trường hợp này.

Đây là kiểm chứng một lỗi đã biết của starter, không phải đánh giá verifier tổng quát. Chưa thể suy rộng sang hidden hoặc model thật. Chi phí là mô phỏng; latency là `unavailable`. Bảng trình bày số làm tròn; số liệu đầy đủ nằm trong report.
