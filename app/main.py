import uvicorn
from fastapi import FastAPI
from decouple import config
from typing import Dict, cast
from app.api.routes import auth

HOST = cast(str, config("HOST", cast=str))
PORT = cast(int, config("PORT", cast=int))
RELOAD = cast(bool, config("RELOAD", cast=bool))

app = FastAPI()

app.include_router(auth.router)


@app.get("/", tags=["sanity"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=RELOAD)
