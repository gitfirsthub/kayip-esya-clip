import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.errors import register_error_handlers
from app.schemas import HealthResponse

VERSION = "0.1.0"

logger = logging.getLogger("app.main")


def check_models(settings: Settings) -> bool:
    """Modellerin diskte olduğunu ve yüklenebildiğini doğrular. Yüz modeli yoksa True/False döner."""
    from sentence_transformers import SentenceTransformer

    for name in (settings.image_model, settings.text_model):
        SentenceTransformer(name, cache_folder=settings.model_cache_dir, device="cpu")

    if not settings.face_blur_enabled:
        logger.warning("Yüz bulanıklaştırma ortam değişkeniyle kapatıldı.")
        return False
    if not os.path.isfile(settings.face_model_path):
        logger.warning("Yüz modeli bulunamadı: %s", settings.face_model_path)
        return False
    try:
        import cv2

        cv2.FaceDetectorYN.create(settings.face_model_path, "", (320, 320))
    except Exception:
        logger.warning("Yüz modeli yüklenemedi.", exc_info=True)
        return False
    return True


def _load(app: FastAPI, settings: Settings) -> None:
    try:
        app.state.face_blur = check_models(settings)
        app.state.models_loaded = True
        app.state.ready = True
    except Exception:
        logger.error("Modeller yüklenemedi.", exc_info=True)
        app.state.load_failed = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    threading.Thread(target=_load, args=(app, settings), daemon=True).start()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Kampüs Kayıp Eşya", version=VERSION, debug=False, lifespan=lifespan)
    app.state.ready = False
    app.state.models_loaded = False
    app.state.face_blur = False
    app.state.load_failed = False
    app.state.item_count = 0

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    @app.get("/health", response_model=HealthResponse)
    async def health():
        if app.state.load_failed:
            return JSONResponse(status_code=503, content={"detail": "Modeller yüklenemedi."})
        if not app.state.ready:
            return JSONResponse(status_code=503, content={"status": "loading"})
        return HealthResponse(
            status="ok",
            models_loaded=app.state.models_loaded,
            face_blur=app.state.face_blur,
            item_count=app.state.item_count,
            version=VERSION,
        )

    return app


app = create_app()
