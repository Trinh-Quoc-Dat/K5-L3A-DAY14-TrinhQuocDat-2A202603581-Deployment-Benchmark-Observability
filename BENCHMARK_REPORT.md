# Benchmark & Observability Report — Day 14

- **Họ tên:** Trịnh Quốc Đạt — 2A202603581
- **Ngày chạy:** 25/11/2026 (GMT+7)
- **Môi trường:** Docker Desktop trên Windows, Python 3.11 Linux trong container, mock LLM.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Giới hạn thời gian chờ của phần lớn người dùng và phát hiện chậm ở đuôi phân phối. |
| Error rate `/ask` | ≤ 2% | Giới hạn tỷ lệ request không hoàn tất thành công. |
| Accuracy trên golden dataset | ≥ 85% ở CI | Chặn bản cập nhật xuống dưới ngưỡng chất lượng. Lần kiểm thử v2 sau khi sửa dùng ngưỡng 100%. |

## 2. Benchmark hiệu năng (develop)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.31 | 189.3 | 217.4 | 1698.2 | 0.33% | PASS |
| 10 | 35.64 | 190.5 | 221.1 | 1689.5 | 2.00% | PASS |
| 50 | 109.65 | 198.6 | 256.8 | 1698.1 | 2.00% | PASS |
| 100 | 42.01 | 531.5 | 4622.2 | 5102.5 | 1.00% | FAIL |

Mỗi mức có 300 request. RPS tăng tới 109.65 ở concurrency 50 rồi giảm còn 42.01 ở mức 100. Tại mức 100, cả median lẫn p95 đều tăng, phù hợp với dấu hiệu bão hòa hoặc xếp hàng. Một lần chạy ở mỗi mức chưa đủ để xác định thành phần nào là nút thắt.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 197.9 | 278.2 | 323.6 |
| 0.03 | 237.5 | 260.1 | 1692.2 |
| 0.1 | 314.4 | 1681.5 | 1712.2 |

Giữa 0 và 0.03, average tăng 39.6 ms trong khi p99 tăng 1,368.6 ms. Ở 0.1, request chậm chiếm đủ tỷ trọng để p95 tăng mạnh. Dùng p95 làm mục tiêu chính và theo dõi p99 để phát hiện đuôi dài khi nhóm request chậm còn nhỏ.

### 2.3 Metric và cardinality

Quan sát `http_requests_total{method="POST",route="/ask",status="200"} 23.0` (counter), `agent_in_flight_requests 0.0` (gauge) và `agent_question_length_chars_count 23.0` (số mẫu của histogram). Histogram độ dài câu hỏi được ghi trước retrieval. Nếu dùng URL thô làm label, mỗi đường dẫn ngẫu nhiên tạo thêm time series và tăng bộ nhớ, lưu trữ, chi phí truy vấn. Dùng mẫu route và gom URL không khớp vào `unmatched` để giới hạn cardinality.

## 3. Benchmark chất lượng (develop)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 sau khi sửa KB |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57.7 | 109.1 | 113.9 |
| Tổng chi phí (USD) | 0.000412 | 0.000762 | 0.000793 |
| Chi phí / câu đúng (USD) | 0.00041235 | 0.00003627 | 0.00003446 |
| Quality gate | FAIL | PASS | PASS |

| ID | Keyword bị thiếu | Thay đổi |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu phân biệt API key và JWT, mô tả chữ ký và thời điểm hết hạn. |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu về Kubernetes HPA và các tín hiệu điều chỉnh số pod. |

Retrieval làm tăng số token và tổng chi phí nhưng giảm chi phí trên mỗi câu đúng nhờ cải thiện độ chính xác. p95 eval từng lần chịu ảnh hưởng của request chậm được giả lập và kích thước mẫu 23 câu. Sau khi sửa KB, hai câu được cải thiện và số regression là 0.

CI có thể khởi động agent v2, đợi /health trả 200 rồi gọi `python eval/run_eval.py --min-accuracy 0.85 --baseline <bao-cao-main.json> --out reports/eval_ci.json`. Giữ exit code của lệnh làm trạng thái của job bắt buộc trên pull request. Nếu accuracy thấp hơn 85% hoặc có regression so với báo cáo trên main, job thất bại và chặn merge.

## 4. Observability stack (production)

### 4.1 Dashboard và metrics

- [Grafana dưới tải](screenshots/grafana-dashboard.png)
- [Jaeger — trace chậm](screenshots/jaeger-slow-trace.png)
- [Jaeger — trace lỗi có exception](screenshots/jaeger-error-trace.png)
- [Prometheus — ba alert cùng firing](screenshots/prometheus-alert-firing.png)

Tại 15:09:30 GMT+7, truy vấn Prometheus trên cửa sổ 1 phút của `POST /ask` cho p95 khoảng **1.898 s** và trung bình **0.588 s**. Khoảng cách này cho thấy một nhóm request chậm kéo dài đuôi phân phối. Hai chuỗi có lưu lượng tại thời điểm truy vấn ghi nhận **14.00** và **13.64 req/s**, khá gần nhau. Đây là quan sát tại một thời điểm, chưa đủ kết luận mức phân phối của mọi replica trong cả lượt chạy.

Input khoảng **1,724.73 token/s** và output khoảng **906.83 token/s**. Agent v2 gửi cả ngữ cảnh lấy từ retrieval cùng câu hỏi, còn phản hồi ngắn hơn. Nginx trả **404** cho `GET /metrics` vì scrape được giới hạn trong mạng Compose. Prometheus gọi trực tiếp từng replica, giữ được số liệu theo instance.

### 4.2 Thí nghiệm cảnh báo

`promtool test rules alert_rules_test.yml` báo **SUCCESS**. Thí nghiệm đầu kết hợp hai thay đổi cấu hình trong cùng lượt Locust. Lượt pause replica được đo riêng từ lúc gửi lệnh pause, sau đó replica được unpause.

| Thay đổi | Alert | Lần đầu quan sát firing | Panel theo dõi |
|---|---|---:|---|
| `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 116.2 s sau lúc cập nhật | Error rate |
| `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 171.5 s sau lúc cập nhật | Latency p95 |
| Tạm pause một replica | `AgentInstanceDown` | 42.6 s sau lúc pause | Instances up |

`LLMCostBurnRateHigh` đã firing trước khi áp dụng lỗi và độ trễ giả lập. Đợt tải nền đã đẩy tốc độ chi phí qua ngưỡng của rule. Ảnh Alerts ghi nhận alert này cùng hai alert lỗi và độ trễ. Thời gian quan sát bao gồm khởi động lại container, tạo lưu lượng, cửa sổ scrape, thời gian giữ điều kiện và khoảng lấy mẫu trạng thái.

### 4.3 Đối chiếu Jaeger và log JSON

Trace chậm `6955c1659e9e228bde394d2f7139d254` kết thúc HTTP 200 trong **1,748.1 ms** theo log request. Span con chiếm phần lớn thời gian là `chat mock-llm-small`, hiển thị khoảng **1.7 s** trên Jaeger. Log đo riêng lời gọi LLM **1,680.4 ms**, khoảng **96.1%** thời gian request.

```json
{"ts": "2026-11-25T08:07:55.315200+00:00", "level": "INFO", "service": "observable-agent", "instance": "b715f46cd243", "event": "llm_call", "trace_id": "6955c1659e9e228bde394d2f7139d254", "span_id": "a3bbc3f32dbb25f6", "request_id": "74a6fbed1df3", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 74, "output_tokens": 37, "cost_usd": 3.3e-05, "llm_ms": 1680.4}
```

Trace lỗi `3ce5d3a54605db534acb5bdaa38b7f73` có event `exception` trong span chat, loại `utils.mock_llm.LLMError`. Request tương ứng trả HTTP 503 trong **858.7 ms** theo log.

```json
{"ts": "2026-11-25T08:07:28.128152+00:00", "level": "INFO", "service": "observable-agent", "instance": "b715f46cd243", "event": "llm_error", "trace_id": "3ce5d3a54605db534acb5bdaa38b7f73", "span_id": "90bd1aad163f3fc8", "request_id": "004b32c14947", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling (production, Locust headless)

100 users, ramp-up 10 users/s, chạy 2 phút cho từng mức. Nguồn là dòng `Aggregated` trong CSV cuối của hai lượt.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---:|---:|---:|---:|---:|
| 1 | 65.58 | 190 | 240 | 1,700 | 84/7,839 |
| 3 | 65.43 | 190 | 280 | 1,700 | 59/7,779 |

Ba replica không cải thiện p95 trong phép đo này. Throughput gần như giữ nguyên và p99 vẫn khoảng 1.7 s. Kết quả phù hợp với workload bị chi phối bởi thời gian chờ của người dùng mô phỏng và độ trễ cố ý trong mock LLM. Hai lượt đo chưa đủ để tách ảnh hưởng của lập lịch container và biến động mẫu ngẫu nhiên. Failures bao gồm HTTP 503 do mock LLM giả lập.

## 6. Kết luận

- Concurrency cao hơn có thể làm throughput giảm và p95 tăng nếu hệ thống bão hòa.
- Average dễ che tác động của một nhóm nhỏ request chậm. Cần quan sát cả p95 và p99.
- Chi phí trên mỗi câu đúng phản ánh hiệu quả chất lượng rõ hơn chi phí trên mỗi request.
- Một thay đổi chất lượng có thể giữ nguyên error rate và latency. Có thể phát hiện bằng eval định kỳ, kiểm thử canary và cảnh báo khi accuracy giảm.
