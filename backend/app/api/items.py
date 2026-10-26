import logging
import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image

from app.api.uploads import read_upload
from app.config import Settings, get_settings
from app.deps import get_blurrer, get_brands, get_campus, get_encoder, get_ocr, get_store, get_tagger, require_ready
from app.errors import ApiError
from app.ml.face_blur import FaceBlurError
from app.ml.image_io import InvalidImageError, load_and_sanitize
from app.ml.ocr import OcrError, confident_words
from app.ml.pii import find_redactions, redact
from app.ml.tags import extract_tags
from app.schemas import Item, ItemList
from app.store import STATUSES

logger = logging.getLogger("app.items")

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])

TURKEY_TZ = timezone(timedelta(hours=3))  # Türkiye'de yaz saati yok; tzdata gerektirmez.
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MSG_NO_IMAGE = "Lütfen bir fotoğraf yükleyin."
MSG_TITLE = "Başlık 3 ile 80 karakter arasında olmalıdır."
MSG_DESCRIPTION = "Açıklama en fazla 500 karakter olabilir."
MSG_LOCATION = "Geçersiz yer."
MSG_DROPOFF = "Geçersiz teslim noktası."
MSG_DATE_FORMAT = "Geçersiz tarih biçimi (YYYY-AA-GG)."
MSG_DATE_FUTURE = "Bulunma tarihi gelecekte olamaz."
def msg_date_old(max_days: int) -> str:
    return f"Bulunma tarihi en fazla {max_days} gün öncesi olabilir."
MSG_BLUR_UNAVAILABLE = "Yüz bulanıklaştırma şu an kullanılamıyor; ilan kaydedilemedi."
MSG_BLUR_FAILED = "Yüz bulanıklaştırma başarısız oldu; ilan kaydedilemedi."
MSG_OCR_FAILED = "Görsel gizlilik kontrolünden geçirilemedi, lütfen tekrar deneyin."
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


def item_text(title: str, description: str, tags: list[str]) -> str:
    """İlanın metin indeksine giren metin: başlık + açıklama + güvenli etiketler."""
    return " ".join(part for part in (title, description, " ".join(tags)) if part)


def redact_and_shrink(img: Image.Image, words, faces: int, brands, max_side: int, min_conf: float):
    """Kişisel veri kutularını siyahla kapatır, güvenli etiketleri çıkarır ve görseli max_side'a küçültür.

    Sansür bütün kelimelere bakar; etiketler yalnızca güveni min_conf ve üstü olan kelimelerden çıkar.
    """
    redaction = find_redactions(words, faces, img.size)
    if redaction.boxes:
        img = redact(img, redaction.boxes)
    tags = [] if redaction.document_like else extract_tags(confident_words(words, min_conf), redaction.boxes, brands)
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img, redaction, tags


def parse_found_date(value: str | None, max_past_days: int) -> date:
    if not value or not DATE_RE.match(value.strip()):
        raise ApiError(422, MSG_DATE_FORMAT)
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        raise ApiError(422, MSG_DATE_FORMAT)
    today = datetime.now(TURKEY_TZ).date()
    if parsed > today:
        raise ApiError(422, MSG_DATE_FUTURE)
    if (today - parsed).days > max_past_days:
        raise ApiError(422, msg_date_old(max_past_days))
    return parsed


def validate_fields(
    title, description, location, found_date, dropoff_point, campus: dict, max_past_days: int
) -> dict:
    title = (title or "").strip()
    if not 3 <= len(title) <= 80:
        raise ApiError(422, MSG_TITLE)
    description = (description or "").strip()
    if len(description) > 500:
        raise ApiError(422, MSG_DESCRIPTION)
    if location not in campus["locations"]:
        raise ApiError(422, MSG_LOCATION)
    parsed = parse_found_date(found_date, max_past_days)
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
    ocr=Depends(get_ocr),
    brands: frozenset[str] = Depends(get_brands),
):
    if image is None:
        raise ApiError(422, MSG_NO_IMAGE)
    data = await read_upload(image, settings.max_upload_mb)
    fields = validate_fields(
        title, description, location, found_date, dropoff_point, campus, settings.found_date_max_days
    )
    # OCR açıkken çalışma kopyası OCR_MAX_SIDE'ta tutulur; küçük metin okunabilsin.
    work_side = max(settings.ocr_max_side, settings.max_image_side) if settings.ocr_enabled else settings.max_image_side
    try:
        img = await run_in_threadpool(load_and_sanitize, data, work_side, settings.max_image_pixels)
    except InvalidImageError as exc:
        raise ApiError(400, exc.message)

    # Bulanıklaştırılmamış görsel hiçbir koşulda saklanmaz.
    if not blurrer.available:
        raise ApiError(503, MSG_BLUR_UNAVAILABLE)
    # Sansürlenmemiş metin de saklanmaz (fail-closed). OCR çıktısı yalnızca bu fonksiyonda yaşar;
    # loglanmaz, diske yazılmaz, yanıta ve hata mesajına girmez.
    words = []
    if settings.ocr_enabled:
        if ocr is None or not ocr.available:
            raise ApiError(503, MSG_OCR_FAILED)
        try:
            words = await run_in_threadpool(ocr.run_ocr, img)
        except OcrError:
            raise ApiError(503, MSG_OCR_FAILED)
    try:
        img, faces = await run_in_threadpool(blurrer.blur, img)
    except FaceBlurError:
        raise ApiError(503, MSG_BLUR_FAILED)
    img, redaction, tags = await run_in_threadpool(
        redact_and_shrink, img, words, faces, brands, settings.max_image_side, settings.ocr_min_conf
    )
    del words

    filename = f"{uuid.uuid4().hex}.jpg"
    directory = uploads_dir(settings)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    try:
        await run_in_threadpool(img.save, path, "JPEG", quality=85)
        embedding = (await run_in_threadpool(encoder.encode_images, [img]))[0]
        text = item_text(fields["title"], fields["description"], tags)
        text_embedding = (await run_in_threadpool(encoder.encode_texts, [text]))[0]
        category, category_score, color = tagger.tag(embedding)
        record = store.add(
            {**fields, "image_path": filename, "category": category, "category_score": category_score,
             "color": color, "faces_blurred": faces, "tags": tags,
             "redacted_regions": len(redaction.boxes), "document_like": redaction.document_like},
            embedding,
            text_embedding,
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
                text_embedding=text_embedding,
                text_weight=settings.search_text_weight,
                high=settings.match_high,
                medium=settings.match_medium,
                image_high=settings.match_image_high,
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
