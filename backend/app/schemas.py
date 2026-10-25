from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    face_blur: bool
    item_count: int
    version: str


class MetaResponse(BaseModel):
    locations: list[str]
    dropoff_points: list[str]
    categories: list[str]
    colors: list[str]
    max_upload_mb: int
