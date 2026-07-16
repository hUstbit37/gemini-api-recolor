# gemini-recolor-service

Service phối màu tường bằng Gemini web app qua thư viện unofficial
[gemini_webapi](https://github.com/HanaokaYuzu/Gemini-API). Đứng độc lập, project
khác gọi qua HTTP — cùng kiểu với `sam2-service/` của tesla-website.

**Chỉ dùng test/demo local.** Thư viện reverse-engineer web app, auth bằng cookie —
vi phạm ToS Google, account có thể bị chặn, license AGPL-3.0. Không deploy production.
Chất lượng: màu chỉ gần đúng hex, chi tiết ảnh bị vẽ lại, ~30s/lần — xem `docs/plan.md`.

## Cấu trúc

```
app/
├── config.py       # đọc env (cookie + tham số service) — nơi duy nhất đọc config
├── models.py       # pydantic request/response (contract của API)
├── client.py       # GeminiClient dùng chung, init 1 lần giữ session
├── image_utils.py  # encode/decode base64 data URL
├── service.py      # pipeline phối màu, raise RecolorError (không dính HTTP)
├── main.py         # FastAPI: /health, /v1/recolor, / (demo)
└── ui.py           # trang demo HTML
run.py              # entrypoint chạy server
recolor.py          # CLI, gọi thẳng app/service.py (không cần bật server)
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # rồi điền cookie
```

Lấy cookie: mở https://gemini.google.com (đã đăng nhập) → `F12` → **Application** →
**Cookies** → copy `__Secure-1PSID` (bắt buộc) và `__Secure-1PSIDTS` vào `.env`.

Lưu ý: đừng mở gemini.google.com bằng chính account đang cho service dùng — hai bên
rotate token đá nhau gây AuthError. Account free hết quota ảnh rất nhanh (theo ngày).

## Chạy

```powershell
.venv\Scripts\python run.py          # http://localhost:8088 (demo UI + API)
.venv\Scripts\python recolor.py --image samples/ngoai-nha.png --color "#3E4E43" --name "Xanh Rung Thong"
```

Swagger: http://localhost:8088/docs

## API

### `GET /health`

```json
{ "status": "ok", "configured": true, "clientReady": true, "model": "BASIC_FLASH" }
```

`configured` = có cookie trong .env. `clientReady` = client đã init (sau request đầu).

### `POST /v1/recolor`

Request:

```json
{
  "imageBase64": "data:image/jpeg;base64,...",
  "colorHex": "#3E4E43",
  "colorName": "Xanh Rừng Thông"
}
```

Response `200`:

```json
{
  "accepted": true,
  "resultImageBase64": "data:image/png;base64,...",
  "colorHex": "#3E4E43",
  "model": "BASIC_FLASH",
  "seconds": 21.4,
  "prompt": "Edit this photo: repaint ONLY the walls ...",
  "savedPath": "D:\\...\\output\\recolor_3E4E43_20260716-231356.png"
}
```

Lỗi → HTTP status + `{"detail": "<message tiếng Việt>"}`:

| Status | Khi nào |
|---|---|
| 401 | Cookie thiếu/hết hạn |
| 422 | Ảnh/màu sai định dạng, ảnh quá lớn |
| 429 | Hết quota ảnh, hoặc Google tạm chặn |
| 502 | Gemini lỗi, hoặc trả text thay vì ảnh |

Ví dụ gọi từ project khác:

```bash
curl -X POST http://localhost:8088/v1/recolor \
  -H "Content-Type: application/json" \
  -d "{\"imageBase64\":\"data:image/png;base64,...\",\"colorHex\":\"#3E4E43\"}"
```

Client chờ tối thiểu **60s** (render ~20-30s, cộng ~6s init lần đầu).

## Config (.env)

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `SECURE_1PSID` | — | bắt buộc |
| `SECURE_1PSIDTS` | — | optional tùy account |
| `GEMINI_RECOLOR_HOST` / `_PORT` | `127.0.0.1` / `8088` | |
| `GEMINI_MODEL` | `BASIC_FLASH` | model duy nhất trả ảnh ổn định |
| `GEMINI_SAVE_OUTPUT` | `1` | `0` = không ghi ảnh ra `output/` |
| `GEMINI_PROMPT_TEMPLATE` | prompt mặc định | phải chứa `{hex}` và `{name_part}` |

Xem `.env.example` cho danh sách đầy đủ.

## Màu bảng TOBIG để test

| Code | Tên | Hex |
|--------|----------------------|-----------|
| AF-101 | Trắng Pha Lê | `#FAF9F6` |
| AF-312 | Be Thảo Nguyên | `#D2C4B1` |
| AF-408 | Xanh Rừng Thông | `#3E4E43` |
| AF-515 | Đất Nung Terracotta | `#A36A5E` |
| AF-204 | Xám Đá Khói | `#A1B2BA` |
