import secrets

from fastapi import Depends, Header, Request

from app.config import Settings, get_settings
from app.errors import ApiError

MSG_LOADING = "Model yükleniyor, birkaç saniye sonra tekrar deneyin."
MSG_FORBIDDEN = "Bu işlem için yetkiniz yok."


def require_ready(request: Request) -> None:
    if not request.app.state.ready:
        raise ApiError(503, MSG_LOADING)


def get_store(request: Request):
    return request.app.state.store


def get_encoder(request: Request):
    return request.app.state.encoder


def get_tagger(request: Request):
    return request.app.state.tagger


def get_blurrer(request: Request):
    return request.app.state.blurrer


def get_campus(request: Request) -> dict:
    return request.app.state.campus


def require_admin(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.admin_token
    if not expected or not x_admin_token:
        raise ApiError(403, MSG_FORBIDDEN)
    if not secrets.compare_digest(x_admin_token.encode("utf-8"), expected.encode("utf-8")):
        raise ApiError(403, MSG_FORBIDDEN)
