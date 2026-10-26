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


class Item(BaseModel):
    id: str
    title: str
    description: str
    location: str
    found_date: str
    dropoff_point: str
    image_url: str
    category: str
    category_score: float
    color: str
    faces_blurred: int
    status: str
    created_at: str


class ItemList(BaseModel):
    items: list[Item]
    total: int


class SearchResult(BaseModel):
    item: Item
    score: float
    match_level: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    took_ms: float


class StatusUpdate(BaseModel):
    status: str


class LostReportCreated(BaseModel):
    tracking_code: str


class ReportMatches(BaseModel):
    created_at: str
    query_text: str
    matches: list[SearchResult]
