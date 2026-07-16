"""Cấu hình service — nơi duy nhất đọc env.

Sau này muốn lấy cookie từ nguồn khác (form nhập, DB, secret manager) thì chỉ
sửa `load_gemini_config` ở đây, các module khác không phải đụng.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SERVICE_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(SERVICE_ROOT / ".env")

HOST = os.environ.get("GEMINI_RECOLOR_HOST", "127.0.0.1")
PORT = int(os.environ.get("GEMINI_RECOLOR_PORT", "8088"))

# Model duy nhất trả ảnh ổn định (test 2026-07-16); mặc định của web app hết
# quota ngay request đầu.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "BASIC_FLASH")
INIT_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_INIT_TIMEOUT", "60"))

MAX_IMAGE_BYTES = int(os.environ.get("GEMINI_MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))

# Lưu ảnh kết quả ra output/ để đối chiếu giữa các lần chạy. Service chạy thật
# thì set 0 — response đã có sẵn base64.
SAVE_OUTPUT = os.environ.get("GEMINI_SAVE_OUTPUT", "1") not in ("0", "false", "False")
OUTPUT_DIR = Path(os.environ.get("GEMINI_OUTPUT_DIR", SERVICE_ROOT / "output"))

PROMPT_TEMPLATE = os.environ.get(
    "GEMINI_PROMPT_TEMPLATE",
    "Edit this photo: repaint ONLY the walls to the exact solid paint color {hex}{name_part}. "
    "Keep absolutely everything else unchanged — same building/room, same furniture and objects, "
    "same doors, windows, roof, floor, ceiling, plants, same lighting and shadows, "
    "same camera angle and framing. Do not redraw or restyle anything. "
    "Photorealistic result, as if the walls were really repainted.",
)


@dataclass
class GeminiConfig:
    secure_1psid: str = ""
    secure_1psidts: str = ""

    def is_complete(self) -> bool:
        """1PSIDTS optional với một số account — chỉ 1PSID là bắt buộc."""
        return bool(self.secure_1psid)


def load_gemini_config() -> GeminiConfig:
    return GeminiConfig(
        secure_1psid=os.environ.get("SECURE_1PSID", "").strip(),
        secure_1psidts=os.environ.get("SECURE_1PSIDTS", "").strip(),
    )
