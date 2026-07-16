"""Pipeline phối màu, tách khỏi transport HTTP.

Dùng chung bởi FastAPI endpoint (`app/main.py`) và CLI (`recolor.py`).
Raise `RecolorError` thay vì `HTTPException` để caller tự map sang transport.
"""

import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path

from gemini_webapi.exceptions import (
    APIError,
    AuthError,
    GeminiError,
    ImageGenerationError,
    TemporarilyBlocked,
    UsageLimitExceeded,
)

from .client import ClientUnavailable, get_client, resolve_model
from .config import (
    GEMINI_MODEL,
    MAX_IMAGE_BYTES,
    OUTPUT_DIR,
    PROMPT_TEMPLATE,
    SAVE_OUTPUT,
)
from .image_utils import decode_data_url, encode_png_data_url
from .models import RecolorRequest, RecolorSuccessResponse

logger = logging.getLogger(__name__)

# Hết quota có khi KHÔNG raise — Gemini trả text kiểu "I can create more images
# as soon as your limit resets" và không kèm ảnh nào.
QUOTA_TEXT_MARKERS = ("limit resets", "limit reset", "reached your limit", "usage in settings")


class RecolorError(Exception):
    """Lỗi mang status HTTP + message hiển thị được cho người dùng."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def build_prompt(color_hex: str, color_name: str | None = None) -> str:
    name_part = f" ({color_name.strip()})" if color_name and color_name.strip() else ""
    return PROMPT_TEMPLATE.format(hex=color_hex.upper(), name_part=name_part)


async def recolor_image(request: RecolorRequest) -> RecolorSuccessResponse:
    color = request.colorHex.upper()
    prompt = build_prompt(color, request.colorName)

    try:
        payload, extension = decode_data_url(request.imageBase64)
    except ValueError as error:
        raise RecolorError(422, str(error)) from error

    if len(payload) > MAX_IMAGE_BYTES:
        raise RecolorError(422, f"Ảnh vượt quá {MAX_IMAGE_BYTES // (1024 * 1024)}MB.")

    try:
        client = await get_client()
        model = resolve_model()
    except ClientUnavailable as error:
        raise RecolorError(
            401, f"Cookie Gemini thiếu/hết hạn ({error}). Cập nhật .env rồi restart."
        ) from error

    # Pass bytes trực tiếp làm Gemini bỏ qua ảnh và tự vẽ nhà khác — phải ghi ra
    # file có đuôi đúng rồi truyền path.
    with tempfile.TemporaryDirectory(prefix="gemini-recolor-") as temp_dir:
        source_path = Path(temp_dir) / f"source{extension}"
        source_path.write_bytes(payload)

        started = time.perf_counter()
        try:
            response = await client.generate_content(prompt, files=[source_path], model=model)
        except UsageLimitExceeded as error:
            raise RecolorError(429, "Account hết quota tạo ảnh. Đợi reset rồi thử lại.") from error
        except TemporarilyBlocked as error:
            raise RecolorError(429, "Google tạm chặn account/IP. Dừng một lúc rồi thử lại.") from error
        except AuthError as error:
            raise RecolorError(401, "Cookie Gemini hết hạn — cập nhật .env rồi restart.") from error
        # APIError KHÔNG kế thừa GeminiError (ImageGenerationError kế thừa APIError),
        # nên phải bắt riêng — nếu không sẽ lọt ra ngoài thành 500.
        except ImageGenerationError as error:
            raise RecolorError(502, f"Gemini không tạo được ảnh: {error}") from error
        except APIError as error:
            raise RecolorError(
                502,
                f"Gemini lỗi tạm thời ({error}). Thử lại sau, hoặc kiểm tra cookie còn hạn không.",
            ) from error
        except GeminiError as error:
            raise RecolorError(502, f"Lỗi Gemini: {error}") from error
        seconds = time.perf_counter() - started

        if not response.images:
            text = (response.text or "").strip()
            if any(marker in text.lower() for marker in QUOTA_TEXT_MARKERS):
                raise RecolorError(429, "Account hết quota tạo ảnh. Đợi reset rồi thử lại.")
            raise RecolorError(
                502, f"Gemini trả text thay vì ảnh: {text[:300] or '(không có nội dung)'}"
            )

        target_dir = OUTPUT_DIR if SAVE_OUTPUT else Path(temp_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"recolor_{color.lstrip('#')}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        saved = await response.images[0].save(
            path=str(target_dir), filename=filename, verbose=False
        )

        result_data_url = encode_png_data_url(saved)

    logger.info("Recolor %s xong sau %.1fs", color, seconds)

    return RecolorSuccessResponse(
        resultImageBase64=result_data_url,
        colorHex=color,
        model=GEMINI_MODEL.upper(),
        seconds=round(seconds, 1),
        prompt=prompt,
        savedPath=str(saved) if SAVE_OUTPUT else None,
    )
