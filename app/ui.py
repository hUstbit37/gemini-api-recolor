"""Trang demo — chỉ để thử tay, không phải phần API của service."""

DEMO_PAGE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gemini Recolor Service — demo</title>
<style>
  :root { font-family: system-ui, "Segoe UI", sans-serif; }
  body { margin: 0; background: #f4f4f2; color: #1e1e1e; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .sub { color: #777; font-size: 13px; margin-bottom: 24px; }
  .sub code { background: #ececeb; padding: 1px 5px; border-radius: 4px; }
  .panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 20px; }
  .row { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }
  .label { font-weight: 600; font-size: 14px; margin-bottom: 8px; display: block; }
  .swatches { display: flex; flex-wrap: wrap; gap: 10px; }
  .swatch { display: flex; align-items: center; gap: 8px; border: 2px solid transparent; border-radius: 8px;
            padding: 6px 10px; background: #fafafa; cursor: pointer; font-size: 13px; }
  .swatch.active { border-color: #1e1e1e; }
  .dot { width: 22px; height: 22px; border-radius: 50%; border: 1px solid #ddd; }
  .custom input[type=color] { width: 26px; height: 26px; border: none; padding: 0; background: none; cursor: pointer; }
  button.go { background: #1e1e1e; color: #fff; border: 0; border-radius: 8px; padding: 12px 28px;
              font-size: 15px; cursor: pointer; }
  button.go:disabled { background: #999; cursor: default; }
  .imgs { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 720px) { .imgs { grid-template-columns: 1fr; } }
  figure { margin: 0; }
  figcaption { font-size: 13px; color: #666; margin-bottom: 6px; font-weight: 600; }
  .frame { background: #eee; border-radius: 10px; min-height: 220px; display: flex;
           align-items: center; justify-content: center; overflow: hidden; }
  .frame img { max-width: 100%; height: auto; display: block; }
  .frame .empty { color: #aaa; font-size: 13px; padding: 40px 10px; }
  .status { font-size: 13px; margin-top: 12px; min-height: 18px; }
  .status.err { color: #c0392b; white-space: pre-wrap; }
  .status.ok { color: #2e7d32; }
  .spin { display: inline-block; width: 14px; height: 14px; border: 2px solid #ccc; border-top-color: #1e1e1e;
          border-radius: 50%; animation: r 0.8s linear infinite; vertical-align: -2px; margin-right: 6px; }
  @keyframes r { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="wrap">
  <h1>Gemini Recolor Service — demo</h1>
  <div class="sub">
    Trang thử tay của service. API thật: <code>POST /v1/recolor</code> · docs: <code>/docs</code> · <code>/health</code>.
    ~30s/lần render, màu chỉ gần đúng — xem README.
  </div>

  <div class="panel">
    <span class="label">1. Chọn ảnh (JPG / PNG / WebP, ≤10MB)</span>
    <input type="file" id="file" accept="image/jpeg,image/png,image/webp">
  </div>

  <div class="panel">
    <span class="label">2. Chọn màu</span>
    <div class="swatches" id="swatches"></div>
  </div>

  <div class="panel row">
    <button class="go" id="go" disabled>Phối màu</button>
    <span class="status" id="status"></span>
  </div>

  <div class="imgs">
    <figure>
      <figcaption>Ảnh gốc</figcaption>
      <div class="frame" id="beforeFrame"><span class="empty">Chưa chọn ảnh</span></div>
    </figure>
    <figure>
      <figcaption id="afterCap">Ảnh sau phối màu</figcaption>
      <div class="frame" id="afterFrame"><span class="empty">Chưa render</span></div>
    </figure>
  </div>
</div>

<script>
const PALETTE = [
  { hex: '#FAF9F6', name: 'Trắng Pha Lê', code: 'AF-101' },
  { hex: '#D2C4B1', name: 'Be Thảo Nguyên', code: 'AF-312' },
  { hex: '#3E4E43', name: 'Xanh Rừng Thông', code: 'AF-408' },
  { hex: '#A36A5E', name: 'Đất Nung Terracotta', code: 'AF-515' },
  { hex: '#A1B2BA', name: 'Xám Đá Khói', code: 'AF-204' },
];

let selected = PALETTE[2];
let file = null;
let busy = false;

const el = (id) => document.getElementById(id);

function fileToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Không đọc được file ảnh.'));
    reader.readAsDataURL(blob);
  });
}

function renderSwatches() {
  const box = el('swatches');
  box.innerHTML = '';
  for (const c of PALETTE) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'swatch' + (selected.code === c.code ? ' active' : '');
    b.innerHTML = `<span class="dot" style="background:${c.hex}"></span>${c.name}<small style="color:#999">&nbsp;${c.code}</small>`;
    b.onclick = () => { selected = c; renderSwatches(); };
    box.appendChild(b);
  }
  const custom = document.createElement('label');
  custom.className = 'swatch custom' + (selected.code === 'CUSTOM' ? ' active' : '');
  custom.innerHTML = `<input type="color" value="${selected.code === 'CUSTOM' ? selected.hex : '#7FA8C9'}">Màu tùy chọn`;
  custom.querySelector('input').oninput = (e) => {
    selected = { hex: e.target.value.toUpperCase(), name: '', code: 'CUSTOM' };
    renderSwatches();
  };
  box.appendChild(custom);
}

el('file').onchange = (e) => {
  file = e.target.files[0] || null;
  if (!file) return;
  const url = URL.createObjectURL(file);
  el('beforeFrame').innerHTML = `<img src="${url}" alt="Ảnh gốc">`;
  el('afterFrame').innerHTML = '<span class="empty">Chưa render</span>';
  updateGo();
};

function updateGo() { el('go').disabled = busy || !file; }

el('go').onclick = async () => {
  if (!file || busy) return;
  busy = true; updateGo();
  const status = el('status');
  status.className = 'status';
  status.innerHTML = '<span class="spin"></span>Đang gửi Gemini... (~30s, đừng bấm lại)';
  el('afterFrame').innerHTML = '<span class="empty">Đang render...</span>';

  const started = performance.now();
  try {
    const imageBase64 = await fileToDataUrl(file);
    const res = await fetch('/v1/recolor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ imageBase64, colorHex: selected.hex, colorName: selected.name || null }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(detailToText(body.detail) || `Lỗi server (${res.status})`);
    el('afterFrame').innerHTML = `<img src="${body.resultImageBase64}" alt="Ảnh sau phối màu">`;
    el('afterCap').textContent = `Ảnh sau phối màu — ${selected.hex}${selected.name ? ' · ' + selected.name : ''}`;
    status.className = 'status ok';
    status.textContent = `Xong sau ${((performance.now() - started) / 1000).toFixed(1)}s`
      + (body.savedPath ? `. Đã lưu: ${body.savedPath}` : '');
  } catch (err) {
    status.className = 'status err';
    status.textContent = err.message;
    el('afterFrame').innerHTML = '<span class="empty">Render thất bại</span>';
  } finally {
    busy = false; updateGo();
  }
};

// FastAPI trả detail dạng string (lỗi của mình) hoặc mảng (validation 422).
function detailToText(detail) {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  return JSON.stringify(detail);
}

renderSwatches();
</script>
</body>
</html>"""
