import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.items import MSG_LOCATION, to_item
from app.api.uploads import read_upload
from app.config import Settings, get_settings
from app.deps import get_campus, get_encoder, get_store, require_ready
from app.errors import ApiError
from app.ml.image_io import InvalidImageError, load_and_sanitize
from app.schemas import LostReportCreated, ReportMatches, SearchResult
from app.tracking import generate_code, hash_code, normalize_code

logger = logging.getLogger("app.lost_reports")

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])

MSG_EMPTY_REPORT = "Bildirim için bir açıklama yazın veya fotoğraf yükleyin."
MSG_QUERY_LONG = "Açıklama en fazla 200 karakter olabilir."
MSG_BAD_CODE = "Takip kodu geçersiz."
MSG_CODE_NOT_FOUND = "Bu takip koduyla bir bildirim bulunamadı."


@router.post("/lost-reports", response_model=LostReportCreated, status_code=201)
async def create_lost_report(
    query: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    location: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    campus: dict = Depends(get_campus),
    store=Depends(get_store),
    encoder=Depends(get_encoder),
):
    query = (query or "").strip()
    if len(query) > 200:
        raise ApiError(422, MSG_QUERY_LONG)
    has_image = image is not None and bool(image.filename)
    if not query and not has_image:
        raise ApiError(422, MSG_EMPTY_REPORT)
    location = location or None
    if location and location not in campus["locations"]:
        raise ApiError(422, MSG_LOCATION)

    # Görsel yalnızca bellekte kodlanır; diske yazılmaz, yalnızca embedding saklanır.
    image_vec = None
    if has_image:
        data = await read_upload(image, settings.max_upload_mb)
        try:
            img = await run_in_threadpool(load_and_sanitize, data, settings.max_image_side, settings.max_image_pixels)
        except InvalidImageError as exc:
            raise ApiError(400, exc.message)
        image_vec = (await run_in_threadpool(encoder.encode_images, [img]))[0]
    text_vec = (await run_in_threadpool(encoder.encode_texts, [query]))[0] if query else None

    code = generate_code()
    report = await run_in_threadpool(store.add_report, hash_code(code), query, location, text_vec, image_vec)
    try:
        await run_in_threadpool(
            lambda: store.match_report_to_items(
                report["id"],
                high=settings.match_high,
                medium=settings.match_medium,
                image_medium=settings.match_image_medium,
            )
        )
    except Exception:
        logger.error("Bildirim mevcut ilanlarla eşleştirilemedi.", exc_info=True)
    return LostReportCreated(tracking_code=code)


@router.get("/lost-reports/{code}/matches", response_model=ReportMatches)
async def report_matches(code: str, store=Depends(get_store)):
    normalized = normalize_code(code)
    if normalized is None:
        raise ApiError(422, MSG_BAD_CODE)
    report = store.get_report_by_code_hash(hash_code(normalized))
    if report is None:
        raise ApiError(404, MSG_CODE_NOT_FOUND)
    matches = [
        SearchResult(item=to_item(item), score=round(score, 4), match_level=level)
        for item, score, level in store.list_matches(report["id"])
    ]
    return ReportMatches(created_at=report["created_at"], query_text=report["query_text"], matches=matches)
