import uvicorn
import logging
from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Dict
from app.core.config import config
from app.core.storage.registry import register_providers
from app.db.listeners import register_listeners
from contextlib import asynccontextmanager
from app.api.routes import (
    auth,
    product,
    variants,
    media,
    upload,
    category,
    product_media,
    cart,
    cart_items,
    address,
    order,
)

HOST = config.HOST
PORT = config.PORT
RELOAD = config.RELOAD

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_providers()
    register_listeners()
    yield


app = FastAPI(lifespan=lifespan)
api = APIRouter(prefix="/api/v1")

api.include_router(auth.router)
api.include_router(product.router)
api.include_router(variants.router)
api.include_router(media.router)
api.include_router(product_media.router)
api.include_router(upload.router)
api.include_router(category.router)
api.include_router(cart.router)
api.include_router(cart_items.router)
api.include_router(address.router)
api.include_router(order.router)
app.include_router(api)


@app.get("/", tags=["Sanity Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    from app.core.errors import ErrorResponse

    payload = ErrorResponse(
        code="INTERNAL_SERVER_ERROR", message="Internal server error"
    ).model_dump()
    return JSONResponse(status_code=500, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from app.core.errors import ErrorResponse

    details = {"errors": exc.errors()}
    payload = ErrorResponse(
        code="VALIDATION_ERROR", message="Validation failed", details=details
    ).model_dump()
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Normalize all HTTPException details into the ErrorResponse JSON shape."""
    from app.core.errors import ErrorResponse

    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        content = detail
    else:
        msg = detail if isinstance(detail, str) else str(detail)
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            500: "INTERNAL_SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        content = ErrorResponse(code=code, message=msg).model_dump()

    return JSONResponse(status_code=exc.status_code, content=content)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
