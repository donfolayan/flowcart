import uvicorn
from fastapi import FastAPI
from decouple import config
from typing import Dict, cast
from app.api.routes import auth
from app.api.routes import product
from app.api.routes import variants
from app.api.routes import media
from app.core.storage.registry import register_providers
from contextlib import asynccontextmanager

HOST = cast(str, config("HOST", cast=str))
PORT = cast(int, config("PORT", cast=int))
RELOAD = cast(bool, config("RELOAD", cast=bool))

app = FastAPI()

app.include_router(auth.router)
app.include_router(product.router)
app.include_router(variants.router)
app.include_router(media.router)


@app.get("/", tags=["Sanity Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_providers()
    yield


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
