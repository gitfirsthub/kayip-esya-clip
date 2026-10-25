"""Sıfır-atış kategori ve renk etiketleyici (CLIP istem embedding'leri ile)."""
import numpy as np

FALLBACK_CATEGORY = "diğer"
FALLBACK_EN = "other"
TEMPLATES = ("avg", "en", "tr")

CATEGORY_EN = "a photo of a {en}"
CATEGORY_TR = "bir {tr} fotoğrafı"
COLOR_EN = "a photo of a {en} object"
COLOR_TR = "{tr} renkli bir nesnenin fotoğrafı"


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    return m / np.linalg.norm(m, axis=1, keepdims=True).clip(min=1e-12)


def _softmax(x: np.ndarray) -> np.ndarray:
    z = x - x.max()
    e = np.exp(z)
    return e / e.sum()


class Tagger:
    """`tag(img_emb) -> (kategori_tr, güven, renk_tr)`; güven = softmax(100·cos) en yüksek olasılık.

    "diğer" istem olarak kodlanmaz; yalnızca güven min_confidence altındayken dönen yedek etikettir.
    """

    def __init__(self, encoder, categories: list[dict], colors: list[dict], template: str = "avg", min_confidence: float = 0.35):
        if template not in TEMPLATES:
            raise ValueError(f"Bilinmeyen şablon: {template}")
        self.template = template
        self.min_confidence = float(min_confidence)
        cats = [c for c in categories if c["tr"] != FALLBACK_CATEGORY and c["en"] != FALLBACK_EN]
        self.category_names = [c["tr"] for c in cats]
        self.color_names = [c["tr"] for c in colors]
        if not self.category_names or not self.color_names:
            raise ValueError("Kategori ve renk listeleri boş olamaz.")
        self.category_embeddings = self._prompts(encoder, cats, CATEGORY_EN, CATEGORY_TR)
        self.color_embeddings = self._prompts(encoder, colors, COLOR_EN, COLOR_TR)

    def _prompts(self, encoder, items: list[dict], en_tpl: str, tr_tpl: str) -> np.ndarray:
        en = [en_tpl.format(en=i["en"]) for i in items]
        tr = [tr_tpl.format(tr=i["tr"]) for i in items]
        if self.template == "en":
            return _normalize(encoder.encode_texts(en))
        if self.template == "tr":
            return _normalize(encoder.encode_texts(tr))
        both = encoder.encode_texts(en + tr)  # tek batch
        n = len(items)
        return _normalize((both[:n] + both[n:]) / 2.0)

    def category_probs(self, img_emb: np.ndarray) -> np.ndarray:
        return _softmax(100.0 * (self.category_embeddings @ self._vec(img_emb)))

    def color_probs(self, img_emb: np.ndarray) -> np.ndarray:
        return _softmax(100.0 * (self.color_embeddings @ self._vec(img_emb)))

    @staticmethod
    def _vec(img_emb: np.ndarray) -> np.ndarray:
        v = np.asarray(img_emb, dtype=np.float32).reshape(-1)
        n = float(np.linalg.norm(v))
        return v / n if n > 0 else v

    def tag(self, img_emb: np.ndarray) -> tuple[str, float, str]:
        cp = self.category_probs(img_emb)
        i = int(np.argmax(cp))
        score = float(cp[i])
        category = self.category_names[i] if score >= self.min_confidence else FALLBACK_CATEGORY
        color = self.color_names[int(np.argmax(self.color_probs(img_emb)))]
        return category, score, color
