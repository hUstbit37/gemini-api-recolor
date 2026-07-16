# Deploy gemini-recolor-test lên VPS bằng pm2

## Context

Service `D:\TQA\gemini-recolor-test` (FastAPI, port 8088) recolor ảnh qua Gemini web cookie, được api/ (NestJS) gọi khi `VISUALIZER_RENDER_BACKEND=gemini` (`api/src/modules/visualizer/clients/gemini-recolor.client.ts`, env `GEMINI_RECOLOR_SERVICE_URL`). User muốn đưa service này lên VPS **cùng máy với api/**, quản lý bằng **pm2**, VPS có **Python 3.10** (đủ — mọi dependency yêu cầu tối đa `>=3.10`; code chỉ dùng syntax 3.10).

Không cần Docker. Thiếu duy nhất file chạy daemon → `ecosystem.config.js` (đã tạo, cần bổ sung) + doc deploy.

## Thay đổi file (repo gemini-recolor-test)

### 1. `ecosystem.config.js` (đã tạo, sửa thêm)
Thêm vào `env`:
```js
TMPDIR: `${__dirname}/.cache`, // gemini_webapi lưu cookie đã rotate vào {tempdir}/gemini_webapi — phải persistent, /tmp là tmpfs mất khi reboot
```
Giữ nguyên phần còn lại: `interpreter: './.venv/bin/python'`, `script: 'run.py'`, fork mode, `GEMINI_RECOLOR_HOST=127.0.0.1` (cùng VPS với api → không expose; service không có auth, CORS `*`).

### 2. `.env.example` — bổ sung các biến server (optional, có default):
```
# GEMINI_RECOLOR_HOST=127.0.0.1
# GEMINI_RECOLOR_PORT=8088
# GEMINI_SAVE_OUTPUT=0
# GEMINI_MODEL=BASIC_FLASH
```

### 3. `.gitignore` — thêm `.cache/`

### 4. `docs/deploy-vps.md` — doc các bước deploy (nội dung = phần "Các bước trên VPS" dưới)

Theo memory plan-to-docs: sau khi plan được duyệt, lưu plan này thành md trong `docs/` của gemini-recolor-test trước khi sửa file.

## Các bước trên VPS (Ubuntu, ghi vào doc — user tự chạy hoặc chạy qua ssh)

```bash
# 1. Copy code (git clone hoặc rsync, loại .venv/ output/)
# 2. Python env — cần python3.10-venv nếu chưa có
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# 3. Config
cp .env.example .env   # điền SECURE_1PSID / SECURE_1PSIDTS MỚI lấy từ browser
mkdir -p .cache        # TMPDIR phải tồn tại trước, không tempfile fallback về /tmp
# 4. pm2
pm2 start ecosystem.config.js
pm2 save && pm2 startup   # tự chạy lại sau reboot
```

## Nối với api/ (tesla-website, cùng VPS)

Trong `api/.env` production:
```
VISUALIZER_RENDER_BACKEND=gemini
GEMINI_RECOLOR_SERVICE_URL=http://127.0.0.1:8088
GEMINI_RECOLOR_TIMEOUT_MS=180000   # Gemini generate 30–90s+, default 120s hơi sát
```

## Lưu ý vận hành (ghi vào doc)

- Cookie lấy xong **đóng tab gemini.google.com, đừng mở lại trên browser đó** — mở lại sẽ rotate `__Secure-1PSIDTS`, giết session service (nguyên nhân chết đêm 16→17/07).
- Cookie chết: log pm2 hiện `Account status: UNAUTHENTICATED`, request trả 502 sau ~2 phút. Xử lý: lấy cookie mới → sửa `.env` → xóa `.cache/gemini_webapi/.cached_cookies_*.json` → `pm2 restart gemini-recolor`.
- IP datacenter khác IP login → Google dễ invalidate session hơn local; đây vẫn là giải pháp không chính thức, không cam kết production (verdict 16/07: SAM2+Sharp là đường chính).

## Verification

1. Trên VPS: `curl http://127.0.0.1:8088/health` → `{"status":"ok","configured":true,...}`.
2. POST `/v1/recolor` với ảnh sample (script test như đã dùng local) → 200, có `resultImageBase64`, `seconds` hợp lý; log pm2 KHÔNG có warning UNAUTHENTICATED.
3. End-to-end: api/ với `VISUALIZER_RENDER_BACKEND=gemini` → gọi visualizer render WALL/ROOM từ web → nhận ảnh recolor.
4. `pm2 restart gemini-recolor` rồi lặp lại bước 2 — xác nhận cookie cache trong `.cache/` sống qua restart.
