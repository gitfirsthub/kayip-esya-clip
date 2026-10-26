"""Yüklenen dosyaları sınırlı okuma ve tür doğrulama yardımcıları."""
import io

from fastapi import UploadFile
from fastapi.responses import JSONResponse
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


# Dosya dışındaki form alanları (başlık, açıklama vb.) için gövde sınırına eklenen pay.
FORM_OVERHEAD_BYTES = 1024 * 1024


class BodySizeLimitMiddleware:
    """Gövdesi MAX_UPLOAD_MB + pay sınırını aşan istekleri 413 ile keser.

    Starlette multipart dosyaları sınırsız olarak /tmp'ye (compose'ta RAM) yazar ve read_upload
    sınırı ancak gövde bütünüyle alındıktan sonra uygular. Content-Length varsa gövde hiç okunmaz;
    yoksa (chunked) okunan bayt sayılır ve sınır aşılınca uygulamanın yanıtı 413 ile değiştirilir.
    """

    def __init__(self, app, max_mb: int):
        self.app = app
        self.max_mb = max_mb
        self.max_bytes = max_mb * 1024 * 1024 + FORM_OVERHEAD_BYTES

    def _response(self) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": msg_too_large(self.max_mb)})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None and length.isdigit() and int(length) > self.max_bytes:
            await self._response()(scope, receive, send)
            return

        received = 0
        exceeded = False
        replaced = False

        async def limited_receive():
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    # Uygulama okumayı bırakır; gövdenin geri kalanı hiç tutulmaz.
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            nonlocal replaced
            if exceeded:
                if not replaced and message["type"] == "http.response.start":
                    replaced = True
                    await self._response()(scope, receive, send)
                return
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not replaced:
                await self._response()(scope, receive, send)


class _BodyTooLarge(Exception):
    pass
