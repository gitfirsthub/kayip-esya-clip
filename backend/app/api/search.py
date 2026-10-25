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
from app.schemas import SearchResponse, SearchResult

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])

MSG_EMPTY_SEARCH = "Aramak için bir açıklama yazın veya fotoğraf yükleyin."
MSG_QUERY_LONG = "Açıklama en fazla 200 karakter olabilir."
MSG_TOP_K = "Sonuç sayısı 1 ile 50 arasında olmalıdır."
MSG_BOOL = "Geçersiz değer: eşyaları teslim edilenlerle birlikte arama seçeneği."

TRUE_VALUES = {"true", "1", "yes", "on"}
FALSE_VALUES = {"false", "0", "no", "off", ""}


def match_level(score: float, settings: Settings) -> str:
    if score >= settings.match_high:
        return "yüksek"
    if score >= settings.match_medium:
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
            img = await run_in_threadpool(load_and_sanitize, data, settings.max_image_side)
        except InvalidImageError as exc:
            raise ApiError(400, exc.message)
        img_vec = (await run_in_threadpool(encoder.encode_images, [img]))[0]
    text_vec = (await run_in_threadpool(encoder.encode_texts, [query]))[0] if query else None

    if text_vec is not None and img_vec is not None:
        vec = 0.5 * text_vec + 0.5 * img_vec  # s = 0.5*cos(q_text,item) + 0.5*cos(q_img,item)
    else:
        vec = text_vec if text_vec is not None else img_vec
    found = await run_in_threadpool(
        lambda: store.search(
            np.asarray(vec, dtype=np.float32),
            location=location,
            category=category,
            include_returned=returned,
            top_k=k,
        )
    )
    results = [
        SearchResult(item=to_item(rec), score=round(score, 4), match_level=match_level(score, settings))
        for rec, score in found
    ]
    return SearchResponse(results=results, took_ms=round((time.perf_counter() - started) * 1000, 1))
