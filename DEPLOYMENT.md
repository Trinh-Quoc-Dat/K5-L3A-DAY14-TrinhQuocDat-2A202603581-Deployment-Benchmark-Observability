# Deployment Information — Day 14

- **Platform:** Render. Docker web service và Key Value tương thích với Redis đều dùng gói Free ở Singapore.
- **Public URL:** [day14-trinhquocdat-agent.onrender.com](https://day14-trinhquocdat-agent.onrender.com)
- **Source:** `main`, commit `87e3521`, Blueprint `06-lab-complete/render.yaml`.
- **Health-check path:** `/health`. `/ready` kiểm tra kết nối Redis qua mạng riêng.

Web service Free có thể ngủ khi không có traffic. Key Value Free giữ dữ liệu trong bộ nhớ và có thể mất state khi chính datastore khởi động lại.

## Cấu hình môi trường

| Biến | Cấu hình trên Render |
|---|---|
| `AGENT_API_KEY` | Render tự sinh từ Blueprint |
| `REDIS_URL` | Connection string nội bộ từ `day14-trinhquocdat-redis` |
| `ENVIRONMENT` | `production` |
| `PORT` | Render cấp cho web service |

## Kiểm thử CP6

Kết quả đo trực tiếp ngày 25/11/2026 bằng HTTP client PowerShell.

| Request | API key | HTTP | Response |
|---|---|---:|---|
| GET `/health` | — | 200 | `{"status":"ok"}` |
| GET `/ready` | — | 200 | `{"status":"ready"}` |
| POST `/ask` | Thiếu | 401 | `{"detail":"Invalid or missing API key"}` |
| POST `/ask` | Hợp lệ | 200 | Câu hỏi Hello và câu trả lời mock |

Lệnh kiểm tra lại bằng Bash. Đặt `AGENT_API_KEY` trong môi trường phiên shell trước khi chạy dòng cuối.

```bash
BASE=https://day14-trinhquocdat-agent.onrender.com
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

## Ảnh bằng chứng

- [Dashboard Render](screenshots/dashboard.png)
- [Deploy succeeded và trạng thái Live](screenshots/running.png)
- [Bốn kết quả HTTP](screenshots/test.png)
