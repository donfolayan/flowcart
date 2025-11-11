import uvicorn
from fastapi import FastAPI, APIRouter
from typing import Dict
from app.core.config import config
from app.core.storage.registry import register_providers
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
)

HOST = config.HOST
PORT = config.PORT
RELOAD = config.RELOAD


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_providers()
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
app.include_router(api)


@app.get("/", tags=["Sanity Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
