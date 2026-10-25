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
    match_high: float = 0.30
    match_medium: float = 0.24
    admin_token: str = ""
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
