import time

import numpy as np
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.items import MSG_BAD_CATEGORY, MSG_LOCATION, to_item
from app.api.uploads import read_upload
from app.config import Settings, get_settings
from app.deps import get_campus, get_encoder, get_store, require_ready
from app.errors import ApiError
from app.ml.image_io import InvalidImageError, load_and_sanitize
from app.ml.tags import query_terms
from app.schemas import SearchResponse, SearchResult

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])

MSG_EMPTY_SEARCH = "Aramak için bir açıklama yazın veya fotoğraf yükleyin."
MSG_QUERY_LONG = "Açıklama en fazla 200 karakter olabilir."
MSG_TOP_K = "Sonuç sayısı 1 ile 50 arasında olmalıdır."
MSG_BOOL = "Geçersiz değer: eşyaları teslim edilenlerle birlikte arama seçeneği."

TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off", ""}


def level_thresholds(settings: Settings, has_text: bool, has_image: bool) -> tuple[float, float]:
    """Sorgu türüne göre (yüksek, orta) eşikleri.

    Görsel-görsel skorları metin-görsel skorlarından çok yüksek (ilgisiz ilanlar bile ~0.5–0.8); bu yüzden
    yalnızca görselle aramada görsel eşikleri, ikisi birlikteyken skor formülüyle aynı oranda (0.5/0.5)
    harmanlanmış eşikler kullanılır.
    """
    if has_text and has_image:
        return (
            0.5 * settings.match_high + 0.5 * settings.match_image_high,
            0.5 * settings.match_medium + 0.5 * settings.match_image_medium,
        )
    if has_image:
        return settings.match_image_high, settings.match_image_medium
    return settings.match_high, settings.match_medium


def match_level(score: float, high: float, medium: float) -> str:
    if score >= high:
        return "yüksek"
    if score >= medium:
        return "orta"
    return "düşük"


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    v = value.strip().lower()
    if v in TRUE_VALUES:
        return True
    if v in FALSE_VALUES:
        return False
    raise ApiError(422, MSG_BOOL)


@router.post("/search", response_model=SearchResponse)
async def search(
    query: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    location: str | None = Form(default=None),
    category: str | None = Form(default=None),
    include_returned: str | None = Form(default=None),
    top_k: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    campus: dict = Depends(get_campus),
    store=Depends(get_store),
    encoder=Depends(get_encoder),
):
    started = time.perf_counter()
    query = (query or "").strip()
    if len(query) > 200:
        raise ApiError(422, MSG_QUERY_LONG)
    has_image = image is not None and bool(image.filename)
    if not query and not has_image:
        raise ApiError(422, MSG_EMPTY_SEARCH)
    location = location or None
    category = category or None
    if location and location not in campus["locations"]:
        raise ApiError(422, MSG_LOCATION)
    if category and category not in [c["tr"] for c in campus["categories"]]:
        raise ApiError(422, MSG_BAD_CATEGORY)
    try:
        k = int(top_k) if top_k not in (None, "") else 12
    except ValueError:
        raise ApiError(422, MSG_TOP_K)
    if not 1 <= k <= 50:
        raise ApiError(422, MSG_TOP_K)
    returned = parse_bool(include_returned)

    # Arama görseli yalnızca bellekte işlenir; diske yazılmaz.
    img_vec = None
    if has_image:
        data = await read_upload(image, settings.max_upload_mb)
        try:
            img = await run_in_threadpool(load_and_sanitize, data, settings.max_image_side, settings.max_image_pixels)
        except InvalidImageError as exc:
            raise ApiError(400, exc.message)
        img_vec = (await run_in_threadpool(encoder.encode_images, [img]))[0]
    text_vec = (await run_in_threadpool(encoder.encode_texts, [query]))[0] if query else None

    terms = frozenset(query_terms(query)) if query else frozenset()

    # s = 0.5*s_text + 0.5*cos(q_img, item); s_text'in metin indeksi ve etiket kısmı store.search'te eklenir.
    if text_vec is not None and img_vec is not None:
        vec = 0.5 * text_vec + 0.5 * img_vec
    else:
        vec = text_vec if text_vec is not None else img_vec
    found = await run_in_threadpool(
        lambda: store.search(
            np.asarray(vec, dtype=np.float32),
            location=location,
            category=category,
            include_returned=returned,
            top_k=k,
            text_vec=text_vec,
            text_weight=settings.search_text_weight,
            text_share=0.5 if img_vec is not None else 1.0,
            query_terms=terms,
            tag_bonus=settings.tag_bonus,
            tag_bonus_max=settings.tag_bonus_max,
        )
    )
    high, medium = level_thresholds(settings, text_vec is not None, img_vec is not None)
    results = [
        SearchResult(item=to_item(rec), score=round(score, 4), match_level=match_level(score, high, medium))
        for rec, score in found
    ]
    return SearchResponse(results=results, took_ms=round((time.perf_counter() - started) * 1000, 1))
