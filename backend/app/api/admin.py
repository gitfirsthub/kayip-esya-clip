import logging
import os

from fastapi import APIRouter, Depends, Response

from app.api.items import MSG_BAD_PAGING, MSG_BAD_STATUS, MSG_NOT_FOUND, to_item, uploads_dir
from app.config import Settings, get_settings
from app.deps import get_store, require_admin, require_ready
from app.errors import ApiError
from app.schemas import AdminMe, Item, ItemList, StatusUpdate
from app.store import STATUSES

logger = logging.getLogger("app.admin")

router = APIRouter(prefix="/api", dependencies=[Depends(require_ready), Depends(require_admin)])


def _owned(store, item_id: str, scope: str | None) -> dict | None:
    """Kapsam dışı ilan 'yok' sayılır; varlığı sızdırılmaz."""
    record = store.get(item_id)
    if record is None or (scope is not None and record["dropoff_point"] != scope):
        return None
    return record


@router.get("/admin/me", response_model=AdminMe)
async def admin_me(scope: str | None = Depends(require_admin)):
    return AdminMe(scope=scope)


@router.get("/admin/items", response_model=ItemList)
async def admin_items(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    scope: str | None = Depends(require_admin),
    store=Depends(get_store),
):
    if status and status not in STATUSES:
        raise ApiError(422, MSG_BAD_STATUS)
    if not 1 <= limit <= 100 or offset < 0:
        raise ApiError(422, MSG_BAD_PAGING)
    records, total = store.list_items(status=status, limit=limit, offset=offset, dropoff_point=scope)
    return ItemList(items=[to_item(r) for r in records], total=total)


@router.patch("/items/{item_id}/status", response_model=Item)
async def update_status(
    item_id: str, body: StatusUpdate, scope: str | None = Depends(require_admin), store=Depends(get_store)
):
    if body.status not in STATUSES:
        raise ApiError(422, MSG_BAD_STATUS)
    if _owned(store, item_id, scope) is None:
        raise ApiError(404, MSG_NOT_FOUND)
    record = store.update_status(item_id, body.status)
    if record is None:
        raise ApiError(404, MSG_NOT_FOUND)
    return to_item(record)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    scope: str | None = Depends(require_admin),
    store=Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    record = _owned(store, item_id, scope)
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
