// pm2 config cho VPS Linux: pm2 start ecosystem.config.js
// Yêu cầu trước đó: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
// và .env đã có SECURE_1PSID / SECURE_1PSIDTS.
module.exports = {
  apps: [
    {
      name: 'gemini-recolor',
      script: 'run.py',
      interpreter: './.venv/bin/python',
      cwd: __dirname,
      exec_mode: 'fork', // uvicorn single-process; cluster mode chỉ dành cho Node
      instances: 1,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      kill_timeout: 10000, // cho lifespan shutdown kịp đóng Gemini client
      env: {
        GEMINI_RECOLOR_HOST: '127.0.0.1', // đổi 0.0.0.0 chỉ khi api gọi từ máy khác — service không có auth
        GEMINI_RECOLOR_PORT: '8088',
        GEMINI_SAVE_OUTPUT: '0',
        PYTHONUNBUFFERED: '1', // log ra pm2 ngay, không buffer
        // gemini_webapi lưu cookie đã rotate vào GEMINI_COOKIE_PATH (mặc định
        // {tempdir}/gemini_webapi — /tmp là tmpfs, mất khi reboot). Trỏ vào repo
        // để cache sống qua reboot; thư viện tự mkdir khi ghi.
        GEMINI_COOKIE_PATH: `${__dirname}/.cache`,
      },
    },
  ],
};
