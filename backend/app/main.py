from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import homestays, bookings, services


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    print(f"{settings.APP_NAME} started — {settings.APP_ENV} mode")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Puri, Odisha travel guide and local services booking platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(homestays.router, prefix="/api/properties", tags=["Properties"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(services.router, prefix="/api/services", tags=["Services"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


@app.get("/api/site-config")
async def site_config():
    from app.schemas import SiteConfigResponse

    return SiteConfigResponse(
        site_name=settings.SITE_NAME,
        site_tagline=settings.SITE_TAGLINE,
        site_phone=settings.SITE_PHONE,
        site_email=settings.SITE_CONTACT_EMAIL,
        caretaker_phone=settings.CARETAKER_PHONE,
        caretaker_name=settings.CARETAKER_NAME,
    )


# Mount static files for assets (CSS, JS, images)
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/css", StaticFiles(directory=str(frontend_path / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")
    app.mount("/images", StaticFiles(directory=str(frontend_path / "images")), name="images")

    # Catch-all route for HTML files
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = frontend_path / full_path

        # If it's a file, serve it
        if file_path.is_file():
            return FileResponse(file_path)

        # If directory, try index.html
        if (file_path / "index.html").is_file():
            return FileResponse(file_path / "index.html")

        # Default to index.html for SPA-like behavior
        index_file = frontend_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        return Response("Not Found", status_code=404)
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
