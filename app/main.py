import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .client import is_ready, reset_client
from .config import GEMINI_MODEL, load_gemini_config
from .models import HealthResponse, RecolorRequest, RecolorSuccessResponse
from .service import RecolorError, recolor_image
from .ui import DEMO_PAGE

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO)
    if not load_gemini_config().is_complete():
        logger.warning("Chưa có SECURE_1PSID trong .env — request đầu tiên sẽ lỗi 401.")
    yield
    await reset_client()


app = FastAPI(title="TOBIG Gemini Recolor Service", version="1.0.0", lifespan=lifespan)

# Service chạy local cho project khác gọi sang — mở CORS cho mọi origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    configured = load_gemini_config().is_complete()
    return HealthResponse(
        status="ok" if configured else "degraded",
        configured=configured,
        clientReady=is_ready(),
        model=GEMINI_MODEL.upper(),
    )


@app.post("/v1/recolor", response_model=RecolorSuccessResponse)
async def recolor(request: RecolorRequest) -> RecolorSuccessResponse:
    try:
        return await recolor_image(request)
    except RecolorError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo() -> str:
    return DEMO_PAGE
