import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .client import is_ready, reset_client
from .config import GEMINI_MODEL, LOG_FILE, load_gemini_config
from .models import HealthResponse, RecolorRequest, RecolorSuccessResponse
from .service import RecolorError, recolor_image
from .ui import DEMO_PAGE

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger().addHandler(file_handler)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
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
    except Exception as error:
        logger.exception("Lỗi không lường trước khi recolor")
        raise HTTPException(
            status_code=500, detail="Có lỗi xảy ra. Vui lòng thử lại sau."
        ) from error


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo() -> str:
    return DEMO_PAGE
