"""Quản lý client Gemini dùng chung.

Client init 1 lần rồi giữ session sống: init lại mỗi request tốn ~6s, và
`GeneratedImage.save` gọi RPC qua session của client nên đóng sớm sẽ lỗi
"Session is closed".
"""

import asyncio
import logging

from gemini_webapi import GeminiClient
from gemini_webapi.constants import Model
from gemini_webapi.exceptions import AuthError

from .config import GEMINI_MODEL, INIT_TIMEOUT_SECONDS, load_gemini_config

logger = logging.getLogger(__name__)

_client: GeminiClient | None = None
_lock = asyncio.Lock()


class ClientUnavailable(Exception):
    """Không dựng được client (thiếu cookie / cookie chết)."""


def resolve_model() -> Model:
    try:
        return Model[GEMINI_MODEL.upper()]
    except KeyError as error:
        valid = ", ".join(m.name for m in Model)
        raise ClientUnavailable(f"GEMINI_MODEL không hợp lệ: {GEMINI_MODEL}. Hợp lệ: {valid}") from error


def is_ready() -> bool:
    return _client is not None


async def get_client() -> GeminiClient:
    global _client
    async with _lock:
        if _client is None:
            config = load_gemini_config()
            if config.is_complete():
                client = GeminiClient(config.secure_1psid, config.secure_1psidts or None)
            else:
                # Không có cookie trong config — thư viện tự dò cookie từ browser local.
                logger.warning("Chưa có cookie trong config, thử đọc cookie từ browser local")
                client = GeminiClient()

            try:
                await client.init(
                    timeout=INIT_TIMEOUT_SECONDS, auto_close=False, auto_refresh=True
                )
            except AuthError as error:
                raise ClientUnavailable(str(error)) from error

            _client = client
    return _client


async def reset_client() -> None:
    """Bỏ client hiện tại — lần gọi kế init lại (dùng khi cookie đổi)."""
    global _client
    async with _lock:
        if _client is not None:
            try:
                await _client.close()
            except Exception:
                logger.debug("Đóng client cũ lỗi, bỏ qua", exc_info=True)
            _client = None
