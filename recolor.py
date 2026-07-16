"""CLI phối màu — chạy thẳng pipeline của service, không cần bật server.

    python recolor.py --image samples/ngoai-nha.png --color "#3E4E43" --name "Xanh Rung Thong"

Auth: cookie đọc qua app/config.py (.env) — xem README.md.
"""

import argparse
import asyncio
import base64
import mimetypes
import re
import sys
from pathlib import Path

from app.client import reset_client
from app.models import HEX_REGEX, RecolorRequest
from app.service import RecolorError, recolor_image

# Console Windows mặc định cp1252 — không in được tiếng Việt trong help/log.
for stream in (sys.stdout, sys.stderr):
    if stream.encoding and stream.encoding.lower() not in ("utf-8", "utf8"):
        stream.reconfigure(encoding="utf-8")

HEX_PATTERN = re.compile(HEX_REGEX)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recolor walls via Gemini web app")
    parser.add_argument("--image", required=True, help="Đường dẫn ảnh nguồn")
    parser.add_argument("--color", required=True, help="Mã màu hex, ví dụ #3E4E43")
    parser.add_argument("--name", default=None, help="Tên màu (optional, thêm vào prompt)")
    args = parser.parse_args()

    if not HEX_PATTERN.match(args.color):
        parser.error(f"Màu không hợp lệ: {args.color} (cần dạng #RGB hoặc #RRGGBB)")
    if not Path(args.image).is_file():
        parser.error(f"Không tìm thấy ảnh: {args.image}")
    return args


def to_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


async def run(args: argparse.Namespace) -> int:
    image_path = Path(args.image)
    print(f"Ảnh  : {image_path}")
    print(f"Màu  : {args.color.upper()}{f' ({args.name})' if args.name else ''}")
    print("Đang gửi ảnh + prompt, chờ Gemini render...\n")

    request = RecolorRequest(
        imageBase64=to_data_url(image_path),
        colorHex=args.color,
        colorName=args.name,
    )

    try:
        result = await recolor_image(request)
    except RecolorError as error:
        print(f"Lỗi ({error.status}): {error.message}", file=sys.stderr)
        return 1
    finally:
        await reset_client()

    print(f"Xong sau {result.seconds}s qua model {result.model}.")
    print(f"Ảnh kết quả: {result.savedPath or '(GEMINI_SAVE_OUTPUT=0 — không lưu file)'}")
    return 0


def main() -> None:
    sys.exit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
