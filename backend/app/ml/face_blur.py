"""OpenCV YuNet ile yüz bulma ve anonimleştirme (pikselleştirme + Gaussian blur)."""
import logging
import os
import threading

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class FaceBlurError(Exception):
    """Model yüklüyken tespit başarısız oldu; görsel yüz bulanıklaştırılmadan kaydedilmemelidir."""


def expand_box(x: float, y: float, w: float, h: float, img_w: int, img_h: int, ratio: float = 0.2) -> tuple[int, int, int, int]:
    """Kutuyu her yönde genişliğin/yüksekliğin `ratio` katı kadar büyütür ve görüntü sınırına kırpar."""
    dx, dy = w * ratio, h * ratio
    x0 = int(max(0, np.floor(x - dx)))
    y0 = int(max(0, np.floor(y - dy)))
    x1 = int(min(img_w, np.ceil(x + w + dx)))
    y1 = int(min(img_h, np.ceil(y + h + dy)))
    return x0, y0, x1, y1


def anonymize_region(arr: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """Kutunun içini önce pikselleştirir, sonra kutu boyutuna oranlı güçlü Gaussian blur uygular.

    Kutunun dışı değişmez. Kanal sırası (RGB/BGR) önemsizdir. Diziyi yerinde değiştirir ve döndürür.
    """
    x0, y0, x1, y1 = box
    region = arr[y0:y1, x0:x1]
    h, w = region.shape[:2]
    if h < 2 or w < 2:
        return arr
    # Pikselleştirme: kısa kenarda ~8 blok.
    block = max(1, min(w, h) // 8)
    small = cv2.resize(region, (max(1, w // block), max(1, h // block)), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    # Kutu boyutuna oranlı tek sayılı çekirdek (en az 3).
    k = max(3, (max(w, h) // 2) | 1)
    arr[y0:y1, x0:x1] = cv2.GaussianBlur(pixelated, (k, k), 0)
    return arr


class FaceBlurrer:
    """Model yoksa, yüklenemezse veya kapalıysa `available=False` olur ve görseli olduğu gibi döndürür.

    Model yüklüyken tespit sırasında hata olursa FaceBlurError fırlatır (kapalı-güvenli): orijinal yüz
    hiçbir koşulda sessizce geçirilmez.
    """

    def __init__(self, model_path: str, score_threshold: float, enabled: bool = True):
        self.model_path = model_path
        self.score_threshold = float(score_threshold)
        self._detector = None
        self._lock = threading.Lock()
        if not enabled:
            logger.warning("Yüz bulanıklaştırma kapalı (FACE_BLUR_ENABLED=false).")
            return
        if not os.path.isfile(model_path):
            logger.warning("Yüz modeli bulunamadı: %s. Yüz bulanıklaştırma devre dışı.", model_path)
            return
        try:
            self._detector = cv2.FaceDetectorYN.create(model_path, "", (320, 320), self.score_threshold)
        except Exception as exc:
            logger.warning("Yüz modeli yüklenemedi (%s). Yüz bulanıklaştırma devre dışı.", exc)
            self._detector = None

    @property
    def available(self) -> bool:
        return self._detector is not None

    def blur(self, img: Image.Image) -> tuple[Image.Image, int]:
        if self._detector is None:
            return img, 0
        try:
            rgb = np.array(img.convert("RGB"))
            h, w = rgb.shape[:2]
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            with self._lock:
                self._detector.setInputSize((w, h))
                _, faces = self._detector.detect(bgr)
            if faces is None or len(faces) == 0:
                return img, 0
            count = 0
            for face in faces:
                if float(face[-1]) < self.score_threshold:
                    continue
                box = expand_box(*face[:4], w, h)
                if box[2] - box[0] < 2 or box[3] - box[1] < 2:
                    continue
                anonymize_region(rgb, box)
                count += 1
            if count == 0:
                return img, 0
            return Image.fromarray(rgb), count
        except Exception as exc:
            logger.error("Yüz bulanıklaştırma sırasında hata: %s", exc)
            raise FaceBlurError("Yüz bulanıklaştırma başarısız oldu.") from exc
