# Day 14 Lab — Mission Answers

## Part 1 — Localhost vs Production

| Anti-pattern trong bản develop | Cách bản production xử lý | Lý do |
|---|---|---|
| Dòng 17–18 ghi API key mẫu và URL database có mật khẩu trong mã | Đọc cấu hình từ biến môi trường qua `config.py` | Tránh lưu thông tin xác thực trong Git. |
| Dòng 21–22 cố định debug và giới hạn token | Đưa cấu hình ra môi trường | Dùng một bản build cho nhiều môi trường. |
| Dòng 33–38 dùng `print` và ghi cả giá trị key | Có logging với formatter JSON | Có thể lọc trường log và tránh ghi bí mật. |
| Thiếu route `/health` và `/ready` | Có liveness và readiness riêng | Hệ thống giám sát tiến trình và quyết định khi nào chuyển traffic. |
| Dòng 51–53 bind localhost, cổng cố định và bật reload | Bind theo cấu hình, tránh reload khi vận hành | Container nhận traffic ngoài loopback và dùng cổng do nền tảng cấp. |
| Thiếu xử lý vòng đời khi dừng | Lifespan ghi nhận việc khởi động và shutdown | Có chỗ dọn tài nguyên và cho request đang chạy kết thúc. |

`curl -i -X POST 'http://localhost:18001/ask?question=Hello'` trả `HTTP/1.1 200 OK` và JSON `{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}`. Cổng 18001 ánh xạ đến app mẫu chạy trong Docker.

## Part 2 — Docker

1. Base image của bản develop là `python:3.11`.
2. Working directory là `/app`.
3. Copy `requirements.txt` trước mã nguồn giúp Docker tái dùng layer cài dependencies khi chỉ sửa mã.
4. `ENTRYPOINT` chọn chương trình chính và các đối số từ `docker run IMAGE ...` được truyền cho chương trình đó. `CMD` là lệnh mặc định nếu thiếu `ENTRYPOINT`, hoặc cung cấp đối số mặc định nếu có `ENTRYPOINT`. Đối số ở cuối lệnh `docker run` ghi đè `CMD`.

`docker images` báo image develop **1.67 GB** và image advanced **240 MB**, giảm khoảng **85.6%** theo giá trị Docker hiển thị. Builder có công cụ biên dịch. Stage runtime dùng bản Python slim và chỉ copy packages đã cài cùng mã nguồn.

Container develop trả `HTTP/1.1 200 OK` khi gọi `POST /ask?question=Hello` qua cổng 18002. Trong stack Compose, request đi từ client qua Nginx đến agent. Redis cung cấp cache và Qdrant cung cấp kho vector qua mạng nội bộ. Gọi qua Nginx quan sát được:

| Request | Kết quả |
|---|---|
| `GET /health` | `HTTP/1.1 200 OK`, `Server: nginx`, JSON có `"status":"ok"`. |
| `POST /ask` với JSON hỏi về Docker | `HTTP/1.1 200 OK`, `Server: nginx`, JSON trả lời về container. |

## Part 3 — Cloud Deployment

Đã deploy Docker web service và Key Value trên Render Free. [URL public](https://day14-trinhquocdat-agent.onrender.com). Kiểm thử CP6 ghi nhận `/health` và `/ready` trả 200, `/ask` thiếu khóa trả 401 và có khóa hợp lệ trả 200. Xem lệnh và ảnh trong [DEPLOYMENT.md](DEPLOYMENT.md).

### Railway và Render

Railway dùng `railway.toml` để chọn Dockerfile và đặt đường dẫn kiểm tra `/health`. Cấu hình của agent lấy API key và URL Redis qua biến môi trường của service.

Render dùng Blueprint YAML để khai báo đồng thời web service và Key Value, chỉ định thư mục nguồn `06-lab-complete` và đường dẫn kiểm tra `/health`. Render sinh API key và cấp kết nối nội bộ đến Key Value cho agent qua biến `REDIS_URL`.

### Exercise 3.3 — Cloud Run

1. Cloud Build cài dependencies và chạy pytest.
2. Sau bước test, Docker build image với tag theo commit và tag `latest`, rồi đẩy cả hai tag lên registry.
3. Pipeline deploy image theo tag commit lên Cloud Run managed tại `asia-southeast1`, khai báo tài nguyên, giới hạn scale, biến môi trường và secret.
4. `service.yaml` là cấu hình khai báo có thể áp dụng bằng `gcloud run services replace`. File mô tả cổng 8000, giới hạn concurrency, liveness probe `/health`, startup probe `/ready` và tham chiếu Secret Manager.

## Part 4 — API Security

### Exercise 4.1–4.3

Trích output `curl -i` từ app mẫu develop khi gửi JSON vào `POST /ask`:

```text
HTTP/1.1 401 Unauthorized
content-type: application/json
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}

HTTP/1.1 200 OK
content-type: application/json
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Lấy token tại `POST /auth/token` bằng tài khoản mẫu. Gửi token trong header `Authorization: Bearer [đã che]`. Mười lần gọi đầu trả `200 OK`, lần 11 trả:

```text
HTTP/1.1 429 Too Many Requests
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
retry-after: 59
content-type: application/json
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4

Bản mẫu kiểm tra ngân sách trước khi gọi mock LLM. Sau khi gọi, nó ước tính token input và output, nhân với giá theo loại token rồi cộng dồn. Vượt ngân sách ngày của user trả `402`. Chạm giới hạn toàn hệ thống trả `503`. Rate limit kiểm soát tần suất trong một cửa sổ thời gian. Cost guard kiểm soát tổng chi phí, vì các request có cùng tần suất có thể dùng số token khác nhau.

## Part 5 — Scaling & Reliability

- Exercise 5.1. App mẫu trả `200` cho `GET /health`, kèm uptime và kiểm tra bộ nhớ. `GET /ready` trả `200` và `"ready":true`. Liveness xác nhận tiến trình đang phục vụ. Readiness cho biết nó có thể nhận traffic.
- Exercise 5.2. Khi shutdown, ngừng nhận request mới, đợi request đang chạy hoàn tất và đóng tài nguyên. Kết quả kiểm tra SIGTERM có request đang chạy được ghi ở Part 6.
- Exercise 5.3. Nếu history nằm trong RAM, mỗi instance thấy một phần hội thoại riêng. Lưu vào Redis theo session ID để các instance truy cập lịch sử chung.
- Exercise 5.4–5.5. Chạy stack với ba bản sao agent sau Nginx. `test_stateless.py` gửi năm request qua ba instance rồi đọc đủ mười tin nhắn của cùng session từ Redis. Script kiểm tra chia sẻ state giữa các instance.

## Part 6 — Production Agent

Agent dùng Redis để chia sẻ giới hạn request và chi phí giữa các worker. /health xác nhận tiến trình vẫn phản hồi. /ready kiểm tra Redis trước khi báo sẵn sàng phục vụ. Uvicorn xử lý SIGTERM và đợi request đang chạy hoàn tất trước khi FastAPI đóng kết nối Redis.

Chạy script chấm đầy đủ trong container Linux với Docker Engine và tham số `--public-url https://day14-trinhquocdat-agent.onrender.com`. Image được script đo là 63 MB. Khi nhận SIGTERM trong lúc xử lý, request trả 200 và tiến trình thoát với mã 0. Docker dừng container trong 0,8 giây với mã 0. Script cũng xác nhận endpoint `/health` công khai trả 200.

```text
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 44/44 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

## AI log

- Yêu cầu AI đọc tài liệu Lab 14 và hướng dẫn sửa TODO nhóm cấu hình và liveness. AI đối chiếu bản khung với script chấm và đưa ra hướng dẫn từng file.
- Sau khi được yêu cầu thao tác trực tiếp, AI triển khai cấu hình, xác thực, rate limit, cost guard, health/readiness, log JSON, vòng đời ứng dụng, Docker Compose và cấu hình deploy. AI chạy bản chấm tĩnh, đạt 28/28 kiểm tra tĩnh. Người học chưa tự sửa hoặc tự chạy kiểm tra trong phiên này.
- AI chạy script chấm đầy đủ trên Linux với toàn bộ repo gắn chỉ đọc. Kết quả PASS 12/12, 43/43 kiểm tra. AI chép checklist từ kết quả thật ở trên.
- AI chạy app mẫu, ghi mã HTTP, kích thước image và kết quả stateless từ các lệnh đã chạy. AI cũng bổ sung histogram độ dài câu hỏi và sửa hai mục knowledge base theo lỗi từ baseline, rồi chạy eval lại đạt 23/23, 0 regression. Số benchmark được lấy từ JSON do các script của lab ghi.
- Người học đăng nhập Render và bàn giao điều khiển. AI cấu hình Blueprint Free, xác minh bốn mã HTTP, sửa lỗi môi trường Python của image observability rồi chạy lại Locust. AI đối chiếu số liệu, alert và trace với CSV, Prometheus, Jaeger và log JSON.
- AI chạy lại script chấm đầy đủ với URL Render và ghi kết quả 44/44 vào checklist.
