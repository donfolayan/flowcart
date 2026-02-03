"""
Flowcart Application Entry Point

This module serves as the entry point for the Flowcart e-commerce API.
The application is created in the factory module to maintain clean separation.
"""

import uvicorn

from app.factory import app
from app.core.config import config

# Re-export app for ASGI servers (uvicorn, gunicorn)
__all__ = ["app"]


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
    )
