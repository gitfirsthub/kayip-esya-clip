import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger("app.errors")

GENERIC_ERROR = "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin."
VALIDATION_ERROR = "Gönderilen bilgiler geçersiz. Lütfen alanları kontrol edin."

HTTP_MESSAGES = {
    404: "Kaynak bulunamadı.",
    405: "Bu yönteme izin verilmiyor.",
}


class ApiError(Exception):
    """İstemciye {"detail": <Türkçe mesaj>} olarak dönen beklenen hata."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _detail_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return _detail_response(422, VALIDATION_ERROR)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return _detail_response(exc.status_code, exc.detail)

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else GENERIC_ERROR
        if detail in ("Not Found", "Method Not Allowed"):
            detail = HTTP_MESSAGES[exc.status_code]
        return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.error("Yakalanmayan hata: %s %s", request.method, request.url.path, exc_info=exc)
        return _detail_response(500, GENERIC_ERROR)
