"""Yüklenen dosyaları sınırlı okuma ve tür doğrulama yardımcıları."""
import io

from fastapi import UploadFile
from PIL import Image

from app.errors import ApiError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
# MPO: birçok telefonun çektiği çok kareli JPEG; Pillow ilk kareyi açar.
ALLOWED_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}
CHUNK_SIZE = 64 * 1024

MSG_UNSUPPORTED = "Desteklenmeyen dosya türü. JPEG, PNG veya WEBP yükleyin."


def msg_too_large(max_mb: int) -> str:
    return f"Dosya çok büyük. En fazla {max_mb} MB yükleyebilirsiniz."


async def read_upload(file: UploadFile, max_mb: int) -> bytes:
    """Dosyayı parça parça okur; sınır aşılınca 413. Başlıktaki tür ve Pillow biçimi doğrulanır (415)."""
    if (file.content_type or "").lower() not in ALLOWED_CONTENT_TYPES:
        raise ApiError(415, MSG_UNSUPPORTED)
    limit = max_mb * 1024 * 1024
    buf = bytearray()
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit:
            raise ApiError(413, msg_too_large(max_mb))
    data = bytes(buf)
    check_format(data)
    return data


def check_format(data: bytes) -> None:
    """Pillow'un tanıdığı biçim izinli listede değilse 415. Hiç tanınmıyorsa açılış hatası 400'e bırakılır."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
    except Exception:
        return
    if fmt not in ALLOWED_FORMATS:
        raise ApiError(415, MSG_UNSUPPORTED)
