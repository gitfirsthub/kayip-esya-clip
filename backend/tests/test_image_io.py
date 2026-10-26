import io

import pytest
from PIL import Image

from app.ml.image_io import InvalidImageError, load_and_sanitize

ORIENTATION = 0x0112
GPS_IFD = 0x8825


def jpeg_with_exif(size=(400, 200), orientation=6) -> bytes:
    img = Image.new("RGB", size, (200, 30, 30))
    exif = Image.Exif()
    exif[ORIENTATION] = orientation
    exif[0x010F] = "Kamera Üreticisi"
    exif.get_ifd(GPS_IFD).update({1: "N", 2: (40.0, 48.0, 30.0), 3: "E", 4: (29.0, 21.0, 0.0)})
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_fixture_really_has_exif():
    img = Image.open(io.BytesIO(jpeg_with_exif()))
    exif = img.getexif()
    assert exif[ORIENTATION] == 6
    assert exif.get_ifd(GPS_IFD)


def test_exif_is_removed_and_orientation_applied():
    img = load_and_sanitize(jpeg_with_exif(size=(400, 200), orientation=6), max_side=1024)
    assert img.size == (200, 400)
    assert img.mode == "RGB"
    assert len(img.getexif()) == 0
    assert "exif" not in img.info

    buf = io.BytesIO()
    img.save(buf, "JPEG")
    reread = Image.open(io.BytesIO(buf.getvalue()))
    assert len(reread.getexif()) == 0


def test_rgba_png_becomes_rgb():
    buf = io.BytesIO()
    Image.new("RGBA", (50, 40), (0, 0, 255, 128)).save(buf, "PNG")
    img = load_and_sanitize(buf.getvalue(), max_side=1024)
    assert img.mode == "RGB"
    assert img.size == (50, 40)


def test_large_image_is_downscaled_small_is_not_upscaled():
    buf = io.BytesIO()
    Image.new("RGB", (3000, 1500), "white").save(buf, "JPEG")
    assert load_and_sanitize(buf.getvalue(), max_side=1024).size == (1024, 512)

    buf = io.BytesIO()
    Image.new("RGB", (300, 100), "white").save(buf, "PNG")
    assert load_and_sanitize(buf.getvalue(), max_side=1024).size == (300, 100)


@pytest.mark.parametrize("data", [b"", b"bu bir metin dosyasi", b"\xff\xd8\xff\xe0" + b"\x00" * 50])
def test_invalid_bytes_raise(data):
    with pytest.raises(InvalidImageError):
        load_and_sanitize(data, max_side=1024)


def test_truncated_jpeg_raises():
    data = jpeg_with_exif()
    with pytest.raises(InvalidImageError):
        load_and_sanitize(data[: len(data) // 2], max_side=1024)


def test_pixel_bomb_rejected_before_decoding():
    # ~21 KB'lık 1-bit PNG, açılınca 177 MP (GB'larca bellek) olurdu.
    buf = io.BytesIO()
    Image.new("1", (13300, 13300), 0).save(buf, "PNG", optimize=True)
    with pytest.warns(Image.DecompressionBombWarning), pytest.raises(InvalidImageError) as exc:
        load_and_sanitize(buf.getvalue(), max_side=1024)
    assert exc.value.message == "Görsel çok büyük; daha küçük bir fotoğraf yükleyin."


@pytest.mark.parametrize("mode", ["RGB", "L", "CMYK"])
def test_large_jpeg_modes_become_rgb_and_shrink(mode):
    buf = io.BytesIO()
    Image.new(mode, (4000, 3000)).save(buf, "JPEG")
    img = load_and_sanitize(buf.getvalue(), max_side=1600)
    assert img.mode == "RGB" and img.size == (1600, 1200)
