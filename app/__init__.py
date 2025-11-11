from fastapi import APIRouter, FastAPI

api_router = APIRouter(prefix="/api")


def attach_api_include(app: FastAPI) -> None:
    """
    Redirect subsequent app.include_router(...) calls to add routes under api_router.
    Call this after mounting api_router on the app.
    """

    def _include_router_to_api(router, **kwargs):
        return api_router.include_router(router, **kwargs)

    app.include_router = _include_router_to_api
