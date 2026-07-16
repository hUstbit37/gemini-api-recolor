"""Encode/decode ảnh dạng base64 data URL."""

import base64
import binascii
import re
from pathlib import Path

DATA_URL_PATTERN = re.compile(r"^data:image/(?P<ext>jpeg|jpg|png|webp);base64,(?P<payload>.+)$")

EXTENSION_BY_MIME = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}


def decode_data_url(data_url: str) -> tuple[bytes, str]:
    """data URL → (bytes, đuôi file). Raise ValueError nếu sai định dạng."""
    match = DATA_URL_PATTERN.match(data_url.strip())
    if not match:
        raise ValueError("Ảnh phải là data URL base64 (data:image/jpeg|png|webp;base64,...)")

    try:
        payload = base64.b64decode(match.group("payload"), validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"Base64 không hợp lệ: {error}") from error

    if not payload:
        raise ValueError("Ảnh trống.")

    return payload, EXTENSION_BY_MIME[match.group("ext")]


def encode_png_data_url(path: str | Path) -> str:
    encoded = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"
