import uvicorn
from typing import Dict
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.core.errors import ErrorResponse
from app.api.routes import (
    address,
    auth,
    cart,
    cart_items,
    category,
    media,
    order,
    payment,
    product,
    product_media,
    promo_code,
    stripe_webhook,
    upload,
    variants,
)
from app.core.config import config
from app.core.logs.logging import setup_logging
from app.core.registry import register_providers
from app.db.listeners import register_listeners
from app.db.logging import setup_db_logging
from app.core.logs.logging_utils import RequestIdMiddleware, get_logger

setup_logging()
setup_db_logging()

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Flowcart application")
    register_providers()
    register_listeners()
    yield
    logger.info("Shutting down Flowcart application")


app = FastAPI(lifespan=lifespan)

# Add request ID middleware for tracing
app.add_middleware(RequestIdMiddleware)

api = APIRouter(prefix="/api/v1")

api.include_router(auth.router)
api.include_router(product.router)
api.include_router(product.admin_router)
api.include_router(variants.router)
api.include_router(variants.admin_router)
api.include_router(media.router)
api.include_router(media.admin_router)
api.include_router(product_media.router)
api.include_router(upload.admin_router)
api.include_router(category.router)
api.include_router(category.admin_router)
api.include_router(cart.router)
api.include_router(cart_items.router)
api.include_router(address.router)
api.include_router(order.router)
api.include_router(order.admin_router)
api.include_router(payment.router)
api.include_router(promo_code.router)
api.include_router(promo_code.admin_router)
api.include_router(stripe_webhook.router)
app.include_router(api)


@app.get("/", tags=["Sanity Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


@app.exception_handler(Exception)
async def handle_unhandled_exception(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else None,
        },
    )
    from app.core.errors import ErrorResponse

    payload = ErrorResponse(
        code="INTERNAL_SERVER_ERROR", message="Internal server error"
    ).model_dump()
    return JSONResponse(status_code=500, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )
    raw = exc.errors() if hasattr(exc, "errors") else str(exc)
    payload = {"detail": raw}
    return JSONResponse(status_code=422, content=jsonable_encoder(payload))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Normalize all HTTPException details into the ErrorResponse JSON shape."""
    logger.warning(
        "HTTP exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
    )

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
    uvicorn.run(
        "app.main:app", host=config.HOST, port=config.PORT, reload=config.RELOAD
    )
