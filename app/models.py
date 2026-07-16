from typing import Literal

from pydantic import BaseModel, Field

HEX_REGEX = r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"
IMAGE_DATA_URL_REGEX = r"^data:image/(jpeg|jpg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$"


class RecolorRequest(BaseModel):
    imageBase64: str = Field(
        ..., description="Ảnh nguồn dạng base64 data URL", pattern=IMAGE_DATA_URL_REGEX
    )
    colorHex: str = Field(..., description="Mã màu hex, vd #3E4E43", pattern=HEX_REGEX)
    colorName: str | None = Field(
        default=None, description="Tên màu, thêm vào prompt để model bám màu sát hơn"
    )


class RecolorSuccessResponse(BaseModel):
    accepted: Literal[True] = True
    resultImageBase64: str = Field(..., description="Ảnh kết quả dạng base64 data URL")
    colorHex: str
    model: str
    seconds: float
    prompt: str
    savedPath: str | None = None


class HealthResponse(BaseModel):
    status: str
    configured: bool
    clientReady: bool
    model: str
