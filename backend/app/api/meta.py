from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_campus, require_ready
from app.schemas import MetaResponse

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready)])


@router.get("/meta", response_model=MetaResponse)
async def meta(campus: dict = Depends(get_campus), settings: Settings = Depends(get_settings)):
    return MetaResponse(
        locations=campus["locations"],
        dropoff_points=campus["dropoff_points"],
        categories=[c["tr"] for c in campus["categories"]],
        colors=[c["tr"] for c in campus["colors"]],
        max_upload_mb=settings.max_upload_mb,
        found_date_max_days=settings.found_date_max_days,
    )
