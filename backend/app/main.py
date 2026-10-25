import json
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
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
    from app.ml.tagger import Tagger
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
    app.state.store = Store(settings.data_dir, dim=encoder.dim)


def _load(app: FastAPI, settings: Settings) -> None:
    try:
        load_components(app, settings)
        app.state.face_blur = app.state.blurrer.available
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
    app.state.store = None

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
            item_count=app.state.store.count() if app.state.store else 0,
            version=VERSION,
        )

    return app


app = create_app()
