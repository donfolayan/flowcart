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
api_router = APIRouter(prefix="/api/v1")

app.include_router(auth.router)
app.include_router(product.router)
app.include_router(variants.router)
app.include_router(media.router)
app.include_router(product_media.router)
app.include_router(upload.router)
app.include_router(category.router)
app.include_router(cart.router)
app.include_router(cart_items.router)


@app.get("/", tags=["Sanity Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
