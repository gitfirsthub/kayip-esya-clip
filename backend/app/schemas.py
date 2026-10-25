from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    face_blur: bool
    item_count: int
    version: str
