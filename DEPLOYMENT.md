# Báo cáo triển khai — Ngày 14

- **Nền tảng:** Render. Dịch vụ web chạy Docker và kho Key Value tương thích với Redis đều dùng gói miễn phí tại Singapore.
- **Địa chỉ công khai:** [day14-trinhquocdat-agent.onrender.com](https://day14-trinhquocdat-agent.onrender.com)
- **Mã nguồn:** `main`, commit `87e3521`, Blueprint `06-lab-complete/render.yaml`.
- **Đường dẫn kiểm tra trạng thái:** `/health`. `/ready` kiểm tra kết nối Redis qua mạng riêng.

Dịch vụ web miễn phí có thể tạm ngừng khi không có lưu lượng. Kho Key Value miễn phí giữ dữ liệu trong bộ nhớ và có thể mất dữ liệu khi khởi động lại.

## Cấu hình môi trường

| Biến | Cấu hình trên Render |
|---|---|
| `AGENT_API_KEY` | Render tự sinh từ Blueprint |
| `REDIS_URL` | Chuỗi kết nối nội bộ từ `day14-trinhquocdat-redis` |
| `ENVIRONMENT` | `production` |
| `PORT` | Render cấp cho web service |

## Kiểm thử CP6

Kết quả đo trực tiếp ngày 25/11/2026 bằng HTTP client PowerShell.

| Yêu cầu HTTP | Khóa API | Mã HTTP | Phản hồi |
|---|---|---:|---|
| GET `/health` | — | 200 | `{"status":"ok"}` |
| GET `/ready` | — | 200 | `{"status":"ready"}` |
| POST `/ask` | Thiếu | 401 | `{"detail":"Invalid or missing API key"}` |
| POST `/ask` | Hợp lệ | 200 | Câu hỏi Hello và câu trả lời giả lập |

Lệnh kiểm tra lại bằng Bash. Đặt `AGENT_API_KEY` trong môi trường phiên shell trước khi chạy dòng cuối.

```bash
BASE=https://day14-trinhquocdat-agent.onrender.com
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

## Ảnh bằng chứng

- [Bảng điều khiển Render](screenshots/dashboard.png)
- [Triển khai thành công và đang hoạt động](screenshots/running.png)
- [Bốn kết quả HTTP](screenshots/test.png)
