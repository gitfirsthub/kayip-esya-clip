import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.api import admin as admin_api
from app.api import items as items_api
from app.api import lost_reports as lost_reports_api
from app.api import meta as meta_api
from app.api import search as search_api
from app.errors import register_error_handlers
from app.schemas import HealthResponse

VERSION = "0.1.0"

logger = logging.getLogger("app.main")

CAMPUS_PATH = Path(__file__).parent / "data" / "campus.json"


def load_campus() -> dict:
    return json.loads(CAMPUS_PATH.read_text(encoding="utf-8"))


def load_components(app: FastAPI, settings: Settings) -> None:
    """Kodlayıcı, yüz bulanıklaştırıcı, etiketleyici ve depoyu oluşturup app.state'e koyar."""
    from app.ml.encoder import ClipEncoder
    from app.ml.face_blur import FaceBlurrer
    from app.ml.ocr import OcrEngine
    from app.ml.tagger import Tagger
    from app.ml.tags import load_brands
    from app.store import Store

    campus = load_campus()
    encoder = ClipEncoder(
        settings.image_model,
        settings.text_model,
        cache_folder=settings.model_cache_dir,
        threads=settings.torch_num_threads,
    )
    app.state.campus = campus
    app.state.encoder = encoder
    app.state.tagger = Tagger(encoder, campus["categories"], campus["colors"])
    app.state.blurrer = FaceBlurrer(
        settings.face_model_path,
        settings.face_score_threshold,
        enabled=settings.face_blur_enabled,
    )
    # OCR_ENABLED=false yalnızca geliştirme içindir; o zaman metin tabanlı kişisel veri sansürlenmez.
    app.state.ocr = (
        OcrEngine(settings.ocr_langs, settings.ocr_timeout_s, settings.ocr_min_conf) if settings.ocr_enabled else None
    )
    if app.state.ocr is None:
        logger.warning("OCR kapalı (OCR_ENABLED=false); görseldeki metin tabanlı kişisel veriler sansürlenmez.")
    app.state.brands = load_brands()
    app.state.store = Store(settings.data_dir, dim=encoder.dim)


def _load(app: FastAPI, settings: Settings) -> None:
    try:
        load_components(app, settings)
        app.state.face_blur = app.state.blurrer.available
        app.state.ocr_available = app.state.ocr is not None and app.state.ocr.available
        app.state.models_loaded = True
        app.state.ready = True
    except Exception:
        logger.error("Modeller yüklenemedi.", exc_info=True)
        app.state.load_failed = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    # tesseract'ın OpenMP iş parçacıkları torch ile çakışmasın (Dockerfile'da da ayarlı).
    os.environ.setdefault("OMP_THREAD_LIMIT", str(settings.omp_thread_limit))
    threading.Thread(target=_load, args=(app, settings), daemon=True).start()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Kampüs Kayıp Eşya", version=VERSION, debug=False, lifespan=lifespan)
    app.state.ready = False
    app.state.models_loaded = False
    app.state.face_blur = False
    app.state.ocr_available = False
    app.state.load_failed = False
    app.state.store = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(meta_api.router)
    app.include_router(items_api.router)
    app.include_router(search_api.router)
    app.include_router(lost_reports_api.router)
    app.include_router(admin_api.router)
    app.mount(
        "/uploads",
        StaticFiles(directory=os.path.join(settings.data_dir, "uploads"), check_dir=False),
        name="uploads",
    )

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
            ocr=app.state.ocr_available,
            item_count=app.state.store.count() if app.state.store else 0,
            version=VERSION,
        )

    return app


app = create_app()
