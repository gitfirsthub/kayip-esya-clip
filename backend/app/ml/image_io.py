"""Yüklenen görseli güvenle açar, yönünü düzeltir, EXIF'i siler ve küçültür."""
import io

from PIL import Image, ImageOps

# Açılmadan önce uygulanan piksel sınırı (≈50 MP; telefon fotoğrafları 12–50 MP). Pillow'un kendi
# sınırı (~89 MP) yalnızca uyarı verir; küçük bir sıkıştırılmış dosya GB'larca bellek açabilir.
MAX_PIXELS = 50_000_000
MSG_TOO_MANY_PIXELS = "Görsel çok büyük; daha küçük bir fotoğraf yükleyin."


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

    Piksel sayısı açılmadan önce MAX_PIXELS ile sınırlanır; JPEG'ler mümkünse küçültülerek çözülür
    (draft) ve görüntü metaveriden arındırılmadan önce küçültülür, böylece tepe bellek sınırlı kalır.
    """
    if not data:
        raise InvalidImageError()
    try:
        with Image.open(io.BytesIO(data)) as probe:
            w, h = probe.size
            if w * h > MAX_PIXELS:
                raise InvalidImageError(MSG_TOO_MANY_PIXELS)
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            img.draft("RGB", (max_side, max_side))  # yalnızca JPEG'de etkili; boyut max_side'ın altına inmez
            img.load()  # kesik dosyalar burada hata verir
            img = ImageOps.exif_transpose(img)
            rgb = _to_rgb(img)
            if max(rgb.size) > max_side:
                rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            # Yalnızca piksellerden yeni görüntü: EXIF, ICC, XMP vb. hiçbir info taşınmaz.
            clean = Image.frombytes("RGB", rgb.size, rgb.tobytes())
    except InvalidImageError:
        raise
    except Image.DecompressionBombError as exc:
        raise InvalidImageError(MSG_TOO_MANY_PIXELS) from exc
    except Exception as exc:  # Pillow çok çeşitli hata tipleri fırlatır (OSError, SyntaxError, ValueError...)
        raise InvalidImageError() from exc
    return clean
