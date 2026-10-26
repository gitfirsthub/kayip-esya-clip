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


def get_ocr(request: Request):
    return request.app.state.ocr


def get_brands(request: Request) -> frozenset[str]:
    return request.app.state.brands


def get_campus(request: Request) -> dict:
    return request.app.state.campus


def _same(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def require_admin(
    x_admin_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str | None:
    """Yetkili kapsamı döndürür: None = tüm noktalar (genel token), str = tek teslim noktası.

    Bütün adaylar sabit zamanlı karşılaştırılır; ilk eşleşmede erken çıkılmaz.
    Örnek değerli veya kısa tokenlar (Settings.token_usable) hiç aday sayılmaz.
    """
    if not x_admin_token:
        raise ApiError(403, MSG_FORBIDDEN)
    scope: str | None = None
    ok = False
    if settings.admin_token_usable and _same(x_admin_token, settings.admin_token):
        ok = True
    for point, token in settings.point_tokens.items():
        if _same(x_admin_token, token) and not ok:
            ok, scope = True, point
    if not ok:
        raise ApiError(403, MSG_FORBIDDEN)
    return scope
