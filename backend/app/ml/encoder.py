"""Çok dilli CLIP kodlayıcı (CPU) ve testler için deterministik sahte kodlayıcı."""
import hashlib
import logging

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_DIM = 512


def _as_matrix(arr: np.ndarray, dim: int) -> np.ndarray:
    return np.ascontiguousarray(arr, dtype=np.float32).reshape(-1, dim)


def _embedding_dim(model) -> int:
    # sentence-transformers 6.x: get_embedding_dimension; eski adı uyarı veriyor.
    getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    return int(getter())


class ClipEncoder:
    """Görseller clip-ViT-B-32, metinler çok dilli metin modeliyle aynı uzaya kodlanır.

    Çıktılar L2-normalize float32 (N, dim) matrislerdir.
    """

    def __init__(self, image_model: str, text_model: str, cache_folder: str, threads: int, batch_size: int = 32):
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(max(1, int(threads)))
        self.batch_size = batch_size
        self.image_model = SentenceTransformer(image_model, cache_folder=cache_folder, device="cpu")
        self.text_model = SentenceTransformer(text_model, cache_folder=cache_folder, device="cpu")
        self.image_model.eval()
        self.text_model.eval()
        img_dim = _embedding_dim(self.image_model)
        txt_dim = _embedding_dim(self.text_model)
        if img_dim != txt_dim:
            raise ValueError(f"Görsel ({img_dim}) ve metin ({txt_dim}) embedding boyutları uyuşmuyor.")
        self.dim = int(img_dim)
        self._warmup()

    def _warmup(self) -> None:
        self.encode_images([Image.new("RGB", (224, 224), (128, 128, 128))])
        self.encode_texts(["ısınma"])
        logger.info("CLIP kodlayıcı hazır (dim=%d, threads=%d).", self.dim, torch.get_num_threads())

    def _encode(self, model, inputs: list) -> np.ndarray:
        # encode([]) (0,) döndürür; boş girdi ayrıca ele alınır.
        if not inputs:
            return np.zeros((0, self.dim), dtype=np.float32)
        with torch.inference_mode():
            out = model.encode(
                inputs,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return _as_matrix(out, self.dim)

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        return self._encode(self.image_model, list(images))

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        return self._encode(self.text_model, list(texts))


class FakeEncoder:
    """ClipEncoder ile aynı arayüz; girdinin SHA-256 özetinden tohumlanan normalize vektörler üretir."""

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim = dim

    def _vector(self, payload: bytes) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
        vec = np.random.default_rng(seed).standard_normal(self.dim)
        return (vec / np.linalg.norm(vec)).astype(np.float32)

    def _stack(self, payloads: list[bytes]) -> np.ndarray:
        if not payloads:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._vector(p) for p in payloads]).astype(np.float32)

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        return self._stack([t.encode("utf-8") for t in texts])

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        payloads = []
        for img in images:
            rgb = img if img.mode == "RGB" else img.convert("RGB")
            payloads.append(rgb.tobytes() + f"{rgb.size[0]}x{rgb.size[1]}".encode())
        return self._stack(payloads)
