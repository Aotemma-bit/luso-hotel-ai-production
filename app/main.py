from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.guests import router as guests_router
from app.api.health import router as health_router
from app.api.requests import router as requests_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware

configure_logging()

app = FastAPI(
    title="Luso Hotel AI",
    description="Secure, tenant-aware hotel operations platform",
    version="2.0.0",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Hotel-ID", "X-Request-ID"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)

for router in (health_router, chat_router, guests_router, requests_router, dashboard_router):
    app.include_router(router, prefix="/api")

project_directory = Path(__file__).resolve().parent.parent
dashboard_directory = project_directory / "dashboard"
app.mount("/dashboard-assets", StaticFiles(directory=dashboard_directory), name="dashboard-assets")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(dashboard_directory / "index.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(dashboard_directory / "index.html")
