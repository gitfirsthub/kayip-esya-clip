"""Build sırasında model ağırlıklarını indirir. Yüz modeli inemezse hata ile çıkar."""
import os
import sys
import urllib.request

from sentence_transformers import SentenceTransformer

IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "clip-ViT-B-32")
TEXT_MODEL = os.environ.get("TEXT_MODEL", "sentence-transformers/clip-ViT-B-32-multilingual-v1")
MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/models")
FACE_MODEL_PATH = os.environ.get("FACE_MODEL_PATH", "/models/face_detection_yunet_2023mar.onnx")

FACE_URLS = [
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
MIN_ONNX_BYTES = 100 * 1024


def is_valid_onnx(path: str) -> bool:
    if not os.path.isfile(path) or os.path.getsize(path) < MIN_ONNX_BYTES:
        return False
    with open(path, "rb") as f:
        return not f.read(64).startswith(b"version https://git-lfs")


def download_face_model() -> None:
    os.makedirs(os.path.dirname(FACE_MODEL_PATH), exist_ok=True)
    for url in FACE_URLS:
        try:
            print(f"Yüz modeli indiriliyor: {url}", flush=True)
            urllib.request.urlretrieve(url, FACE_MODEL_PATH)
        except Exception as exc:
            print(f"İndirme başarısız: {exc}", file=sys.stderr)
            continue
        if is_valid_onnx(FACE_MODEL_PATH):
            print("Yüz modeli hazır.", flush=True)
            return
        print("İndirilen dosya geçerli bir ONNX değil (LFS pointer olabilir).", file=sys.stderr)
    sys.exit("HATA: YuNet yüz modeli indirilemedi.")


def main() -> None:
    os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
    for name in (IMAGE_MODEL, TEXT_MODEL):
        print(f"Model indiriliyor: {name}", flush=True)
        SentenceTransformer(name, cache_folder=MODEL_CACHE_DIR, device="cpu")
    download_face_model()


if __name__ == "__main__":
    main()
