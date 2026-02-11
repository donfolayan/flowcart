import uvicorn

from app.factory import app
from app.core.config import config

__all__ = ["app"]


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
    )
