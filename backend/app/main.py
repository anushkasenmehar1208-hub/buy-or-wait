"""FastAPI application factory/entry — wires router, CORS, and error handling."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import app_error_handler
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Buy or Wait? API",
        version="1.0.0",
        description="Personal financial decision assistant powered by a deterministic "
                    "90-day cash-flow engine.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return app_error_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        fields = []
        for err in exc.errors()[:10]:
            cleaned = {k: v for k, v in err.items() if k in ("loc", "msg", "type")}
            cleaned["loc"] = [str(x) for x in cleaned.get("loc", [])]
            fields.append(cleaned)
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "ValidationError", "message": "Invalid request",
                               "details": {"fields": fields}}},
        )

    @app.get("/api/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
