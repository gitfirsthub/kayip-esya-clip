"""Bir görselde yüz bulanıklaştırmayı elle denemek için.

Kullanım (backend/ dizininden):
    python scripts/try_blur.py <girdi> <çıktı> [--model YOL] [--threshold 0.6]
Çıktıyı backend/data/ altına yazın (git'e girmez).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings  # noqa: E402
from app.ml.face_blur import FaceBlurrer  # noqa: E402
from app.ml.image_io import InvalidImageError, load_and_sanitize  # noqa: E402


def warn_if_tracked(path: Path) -> None:
    """Çıktı depo içinde ve git tarafından yok sayılmıyorsa uyarır."""
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=BACKEND_DIR, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return
    resolved = path.resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        return
    ignored = subprocess.run(["git", "check-ignore", "-q", str(resolved)], cwd=root).returncode == 0
    if not ignored:
        print(
            f"UYARI: {resolved} depo içinde ve git tarafından yok sayılmıyor; yanlışlıkla commit'lenebilir. "
            f"Çıktıyı {BACKEND_DIR / 'data'} altına yazmanız önerilir.",
            file=sys.stderr,
        )


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="YuNet ile yüz bulanıklaştırma denemesi")
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--model", default=settings.face_model_path)
    parser.add_argument("--threshold", type=float, default=settings.face_score_threshold)
    args = parser.parse_args()

    local = BACKEND_DIR / "data" / "models" / "face_detection_yunet_2023mar.onnx"
    model_path = args.model
    if not os.path.isfile(model_path) and local.is_file():
        model_path = str(local)

    blurrer = FaceBlurrer(model_path, args.threshold)
    if not blurrer.available:
        print(f"HATA: Yüz modeli yüklenemedi: {model_path}", file=sys.stderr)
        return 1
    try:
        img = load_and_sanitize(Path(args.input).read_bytes(), settings.max_image_side)
    except (OSError, InvalidImageError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1

    out, n_faces = blurrer.blur(img)
    out_path = Path(args.output)
    warn_if_tracked(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, "JPEG", quality=85)
    print(f"{n_faces} yüz bulanıklaştırıldı. Çıktı: {out_path} ({out.size[0]}x{out.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
