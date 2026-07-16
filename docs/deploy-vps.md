# Deploy lên VPS bằng pm2

Service chạy **cùng VPS với backend api/** (tesla-website), bind `127.0.0.1` — không expose ra internet vì service không có auth và CORS mở `*`. Yêu cầu VPS: Python ≥ 3.10, Node + pm2.

## Các bước

```bash
# 1. Copy code lên VPS (git clone hoặc rsync), KHÔNG copy .venv/ và output/

# 2. Python venv (cần gói python3.10-venv nếu chưa có: apt install python3.10-venv)
cd gemini-recolor-test
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Config
cp .env.example .env
#    -> điền SECURE_1PSID / SECURE_1PSIDTS MỚI (lấy từ browser, xem mục Cookie dưới)
#    Cookie cache: ecosystem.config.js set GEMINI_COOKIE_PATH=./.cache —
#    gemini_webapi lưu token đã rotate vào đó (thư viện tự tạo thư mục).
#    Không set thì cache vào /tmp (tmpfs) -> reboot là mất token rotate.

# 4. pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup        # in ra lệnh sudo — chạy lệnh đó để tự start sau reboot
```

## Nối với api/ (cùng VPS)

`api/.env` production:

```env
VISUALIZER_RENDER_BACKEND=gemini
GEMINI_RECOLOR_SERVICE_URL=http://127.0.0.1:8088
GEMINI_RECOLOR_TIMEOUT_MS=180000   # Gemini generate 30-90s+, default 120s hơi sát
```

## Cookie — lấy và giữ sống

1. Mở https://gemini.google.com (đã login) → F12 → Application → Cookies → copy `__Secure-1PSID` và `__Secure-1PSIDTS` vào `.env`.
2. **Lấy xong đóng tab và đừng mở lại gemini.google.com trên browser đó.** Mở lại sẽ rotate `__Secure-1PSIDTS` phía Google, giết session của service (đây là nguyên nhân service chết đêm 16→17/07/2026).
3. Service tự refresh token định kỳ (`auto_refresh=True`) và cache vào `.cache/.cached_cookies_<1PSID>.json`.

## Khi cookie chết

Dấu hiệu: log pm2 (`pm2 logs gemini-recolor`) lặp `Account status: UNAUTHENTICATED`, request `/v1/recolor` trả 502 sau ~2 phút.

Xử lý:

```bash
# 1. Lấy cookie mới từ browser, sửa .env
# 2. Xóa cache cũ (init thử cache TRƯỚC .env — cache stale sẽ đè cookie mới):
rm -f .cache/.cached_cookies_*.json
# 3.
pm2 restart gemini-recolor
```

## Kiểm tra sau deploy

```bash
curl http://127.0.0.1:8088/health
# -> {"status":"ok","configured":true,"clientReady":...,"model":"BASIC_FLASH"}

# Test recolor thật (mất ~30-90s):
.venv/bin/python - <<'EOF'
import base64, json, urllib.request
img = open("samples/ngoai-nha.png", "rb").read()
body = json.dumps({
    "imageBase64": "data:image/png;base64," + base64.b64encode(img).decode(),
    "colorHex": "#3E4E43",
}).encode()
req = urllib.request.Request("http://127.0.0.1:8088/v1/recolor", data=body,
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=300) as resp:
    payload = json.loads(resp.read())
    print("OK", payload["seconds"], "s, result", len(payload["resultImageBase64"]), "bytes")
EOF

# Sống qua restart (cookie cache persistent):
pm2 restart gemini-recolor   # rồi chạy lại test trên
```

## Giới hạn đã biết

- Đây là cookie session cá nhân (gemini_webapi, không phải API chính thức). IP datacenter khác IP login → Google dễ invalidate session hơn chạy local; xác định trước là cookie sẽ chết định kỳ và phải thay tay.
- Không dùng làm đường render chính cho production — verdict 16/07/2026: SAM2 + Sharp (`VISUALIZER_RENDER_BACKEND=local`) là đường chính, gemini là backend thử nghiệm.
