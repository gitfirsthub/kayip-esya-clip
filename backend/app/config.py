import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:3000"
    data_dir: str = "/data"
    model_cache_dir: str = "/models"
    image_model: str = "clip-ViT-B-32"
    text_model: str = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
    face_model_path: str = "/models/face_detection_yunet_2023mar.onnx"
    face_blur_enabled: bool = True
    face_score_threshold: float = 0.6
    max_upload_mb: int = 8
    max_image_side: int = 1024
    torch_num_threads: int = 4
    match_high: float = 0.315
    match_medium: float = 0.255
    match_image_medium: float = 0.80
    admin_token: str = ""
    admin_point_tokens: str = ""  # JSON: {"<teslim noktası>": "<token>"}
    ocr_enabled: bool = True
    ocr_langs: str = "tur+eng"
    ocr_max_side: int = 1600
    ocr_timeout_s: float = 8
    ocr_min_conf: float = 30
    omp_thread_limit: int = 1
    search_text_weight: float = 0.1
    tag_bonus: float = 0.05
    tag_bonus_max: float = 0.10
    log_level: str = "INFO"

    @property
    def point_tokens(self) -> dict[str, str]:
        """Teslim noktası -> token. Bozuk JSON güvenli tarafta boş sayılır (nokta tokenları kapalı)."""
        if not self.admin_point_tokens.strip():
            return {}
        try:
            data = json.loads(self.admin_point_tokens)
        except ValueError:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): v for k, v in data.items() if isinstance(v, str) and v}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
