from typing import Dict, cast, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.core.logs.logging import setup_logging
from app.core.logs.logging_utils import RequestIdMiddleware, get_logger
from app.core.middleware import SecurityHeadersMiddleware
from app.db.logging import setup_db_logging
from app.db.session import get_session

# Initialize logging early
setup_logging()
setup_db_logging()

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Deferred imports to avoid circular dependencies
    from app.core.registry import register_providers
    from app.db.listeners import register_listeners
    
    logger.info("Starting up Flowcart application")
    register_providers()
    register_listeners()
    yield
    logger.info("Shutting down Flowcart application")


def create_app() -> FastAPI:
    """Application factory function."""
    application = FastAPI(
        lifespan=lifespan,
        title="Flowcart API",
        description="E-commerce backend API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure rate limiter
    from app.api.routes.auth import limiter
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded, cast(Callable, _rate_limit_exceeded_handler)
    )

    # Add middleware (order matters - last added is first executed)
    if config.ENVIRONMENT == "production":
        application.add_middleware(HTTPSRedirectMiddleware)

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[config.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    from app.core.exception_handlers import register_exception_handlers
    register_exception_handlers(application)

    # Register routes
    _register_routes(application)

    return application


def _register_routes(app: FastAPI) -> None:
    """Register all API routes."""
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
        users,
    )

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
    api.include_router(users.router)
    api.include_router(users.admin_router)
    api.include_router(stripe_webhook.router)

    app.include_router(api)

    # Health check endpoints
    @app.get("/", tags=["Sanity Check"])
    def read_root() -> Dict[str, str]:
        return {"msg": "Application is running"}

    @app.get("/health", tags=["Health Check"])
    async def health_check(db: AsyncSession = Depends(get_session)) -> Dict[str, str]:
        """Health check endpoint to verify application and database connectivity."""
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            logger.error("Database connectivity check failed", exc_info=e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connectivity check failed",
            ) from e
        return {"status": "ok"}


# Create the app instance
app = create_app()