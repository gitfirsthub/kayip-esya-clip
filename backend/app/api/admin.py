import logging
import os

from fastapi import APIRouter, Depends, Response

from app.api.items import MSG_BAD_STATUS, MSG_NOT_FOUND, to_item, uploads_dir
from app.config import Settings, get_settings
from app.deps import get_store, require_admin, require_ready
from app.errors import ApiError
from app.schemas import Item, StatusUpdate
from app.store import STATUSES

logger = logging.getLogger("app.admin")

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready), Depends(require_admin)])


@router.patch("/items/{item_id}/status", response_model=Item)
async def update_status(item_id: str, body: StatusUpdate, store=Depends(get_store)):
    if body.status not in STATUSES:
        raise ApiError(422, MSG_BAD_STATUS)
    record = store.update_status(item_id, body.status)
    if record is None:
        raise ApiError(404, MSG_NOT_FOUND)
    return to_item(record)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: str, store=Depends(get_store), settings: Settings = Depends(get_settings)):
    record = store.get(item_id)
    if record is None or not store.delete(item_id):
        raise ApiError(404, MSG_NOT_FOUND)
    path = os.path.join(uploads_dir(settings), record["image_path"])
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Görsel dosyası silinemedi: %s", path)
    return Response(status_code=204)
