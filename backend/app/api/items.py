import logging
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.uploads import read_upload
from app.config import Settings, get_settings
from app.deps import get_blurrer, get_campus, get_encoder, get_store, get_tagger, require_ready
from app.errors import ApiError
from app.ml.face_blur import FaceBlurError
from app.ml.image_io import InvalidImageError, load_and_sanitize
from app.schemas import Item, ItemList
from app.store import STATUSES

logger = logging.getLogger("app.items")

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])

TURKEY_TZ = timezone(timedelta(hours=3))  # Türkiye'de yaz saati yok; tzdata gerektirmez.
MAX_PAST_DAYS = 60
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MSG_NO_IMAGE = "Lütfen bir fotoğraf yükleyin."
MSG_TITLE = "Başlık 3 ile 80 karakter arasında olmalıdır."
MSG_DESCRIPTION = "Açıklama en fazla 500 karakter olabilir."
MSG_LOCATION = "Geçersiz yer."
MSG_DROPOFF = "Geçersiz teslim noktası."
MSG_DATE_FORMAT = "Geçersiz tarih biçimi (YYYY-AA-GG)."
MSG_DATE_FUTURE = "Bulunma tarihi gelecekte olamaz."
MSG_DATE_OLD = "Bulunma tarihi en fazla 60 gün öncesi olabilir."
MSG_BLUR_UNAVAILABLE = "Yüz bulanıklaştırma şu an kullanılamıyor; ilan kaydedilemedi."
MSG_BLUR_FAILED = "Yüz bulanıklaştırma başarısız oldu; ilan kaydedilemedi."
MSG_NOT_FOUND = "İlan bulunamadı."
MSG_BAD_STATUS = "Geçersiz durum."
MSG_BAD_CATEGORY = "Geçersiz kategori."
MSG_BAD_PAGING = "Geçersiz sayfalama değeri."


def uploads_dir(settings: Settings) -> str:
    return os.path.join(settings.data_dir, "uploads")


def to_item(record: dict) -> Item:
    data = {k: v for k, v in record.items() if k != "image_path"}
    data["image_url"] = f"/uploads/{record['image_path']}"
    return Item(**data)


def parse_found_date(value: str | None) -> date:
    if not value or not DATE_RE.match(value.strip()):
        raise ApiError(422, MSG_DATE_FORMAT)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        raise ApiError(422, MSG_DATE_FORMAT)
    today = datetime.now(TURKEY_TZ).date()
    if parsed > today:
        raise ApiError(422, MSG_DATE_FUTURE)
    if (today - parsed).days > MAX_PAST_DAYS:
        raise ApiError(422, MSG_DATE_OLD)
    return parsed


def validate_fields(title, description, location, found_date, dropoff_point, campus: dict) -> dict:
    title = (title or "").strip()
    if not 3 <= len(title) <= 80:
        raise ApiError(422, MSG_TITLE)
    description = (description or "").strip()
    if len(description) > 500:
        raise ApiError(422, MSG_DESCRIPTION)
    if location not in campus["locations"]:
        raise ApiError(422, MSG_LOCATION)
    parsed = parse_found_date(found_date)
    if dropoff_point not in campus["dropoff_points"]:
        raise ApiError(422, MSG_DROPOFF)
    return {
        "title": title,
        "description": description,
        "location": location,
        "found_date": parsed.isoformat(),
        "dropoff_point": dropoff_point,
    }


@router.post("/items", response_model=Item, status_code=201)
async def create_item(
    image: UploadFile | None = File(default=None),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    location: str | None = Form(default=None),
    found_date: str | None = Form(default=None),
    dropoff_point: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    campus: dict = Depends(get_campus),
    store=Depends(get_store),
    encoder=Depends(get_encoder),
    tagger=Depends(get_tagger),
    blurrer=Depends(get_blurrer),
):
    if image is None:
        raise ApiError(422, MSG_NO_IMAGE)
    data = await read_upload(image, settings.max_upload_mb)
    fields = validate_fields(title, description, location, found_date, dropoff_point, campus)
    try:
        img = await run_in_threadpool(load_and_sanitize, data, settings.max_image_side)
    except InvalidImageError as exc:
        raise ApiError(400, exc.message)

    # Bulanıklaştırılmamış görsel hiçbir koşulda saklanmaz.
    if not blurrer.available:
        raise ApiError(503, MSG_BLUR_UNAVAILABLE)
    try:
        img, faces = await run_in_threadpool(blurrer.blur, img)
    except FaceBlurError:
        raise ApiError(503, MSG_BLUR_FAILED)

    filename = f"{uuid.uuid4().hex}.jpg"
    directory = uploads_dir(settings)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    try:
        await run_in_threadpool(img.save, path, "JPEG", quality=85)
        embedding = (await run_in_threadpool(encoder.encode_images, [img]))[0]
        category, category_score, color = tagger.tag(embedding)
        record = store.add(
            {**fields, "image_path": filename, "category": category, "category_score": category_score,
             "color": color, "faces_blurred": faces},
            embedding,
        )
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    # Eşleştirme ek bir özelliktir; hata verirse ilan kaydı yine de başarılı döner.
    try:
        await run_in_threadpool(
            lambda: store.match_item_to_reports(
                record["id"],
                record["location"],
                embedding,
                high=settings.match_high,
                medium=settings.match_medium,
                image_medium=settings.match_image_medium,
            )
        )
    except Exception:
        logger.error("İlan açık bildirimlerle eşleştirilemedi.", exc_info=True)
    return to_item(record)


@router.get("/items", response_model=ItemList)
async def list_items(
    status: str | None = None,
    location: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
    campus: dict = Depends(get_campus),
    store=Depends(get_store),
):
    if status and status not in STATUSES:
        raise ApiError(422, MSG_BAD_STATUS)
    if location and location not in campus["locations"]:
        raise ApiError(422, MSG_LOCATION)
    if category and category not in [c["tr"] for c in campus["categories"]]:
        raise ApiError(422, MSG_BAD_CATEGORY)
    if not 1 <= limit <= 100 or offset < 0:
        raise ApiError(422, MSG_BAD_PAGING)
    records, total = store.list_items(status=status, location=location, category=category, limit=limit, offset=offset)
    return ItemList(items=[to_item(r) for r in records], total=total)


@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: str, store=Depends(get_store)):
    record = store.get(item_id)
    if record is None:
        raise ApiError(404, MSG_NOT_FOUND)
    return to_item(record)
