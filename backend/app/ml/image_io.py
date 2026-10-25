"""Yüklenen görseli güvenle açar, yönünü düzeltir, EXIF'i siler ve küçültür."""
import io

from PIL import Image, ImageOps


class InvalidImageError(Exception):
    """Görsel açılamadığında veya bozuk olduğunda fırlatılır."""

    def __init__(self, message: str = "Görsel açılamadı. Lütfen geçerli bir JPEG, PNG veya WEBP dosyası yükleyin."):
        super().__init__(message)
        self.message = message


def _to_rgb(img: Image.Image) -> Image.Image:
    """Her modu RGB'ye çevirir; şeffaf alanlar beyaz arka planla birleştirilir."""
    if img.mode == "P" and "transparency" in img.info:
        img = img.convert("RGBA")
    if img.mode in ("RGBA", "LA", "PA"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def load_and_sanitize(data: bytes, max_side: int) -> Image.Image:
    """Baytlardan EXIF/metaveri taşımayan, en uzun kenarı en fazla max_side olan RGB görüntü üretir.

    Pillow'un decompression-bomb koruması (Image.MAX_IMAGE_PIXELS) olduğu gibi kalır.
    """
    if not data:
        raise InvalidImageError()
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.load()  # kesik dosyalar burada hata verir
            img = ImageOps.exif_transpose(img)
            rgb = _to_rgb(img)
            # Yalnızca piksellerden yeni görüntü: EXIF, ICC, XMP vb. hiçbir info taşınmaz.
            clean = Image.frombytes("RGB", rgb.size, rgb.tobytes())
    except InvalidImageError:
        raise
    except Image.DecompressionBombError as exc:
        raise InvalidImageError("Görsel çok büyük; daha küçük bir fotoğraf yükleyin.") from exc
    except Exception as exc:  # Pillow çok çeşitli hata tipleri fırlatır (OSError, SyntaxError, ValueError...)
        raise InvalidImageError() from exc

    if max(clean.size) > max_side:
        clean.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return clean
