import uvicorn
from fastapi import FastAPI
from decouple import config
from typing import Dict, cast

HOST = cast(str, config("HOST", cast=str))
PORT = cast(int, config("PORT", cast=int))
RELOAD = cast(bool, config("RELOAD", cast=bool))

app = FastAPI()


@app.get("/", tags=["Health Check"])
def read_root() -> Dict[str, str]:
    return {"msg": "Application is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=RELOAD)
