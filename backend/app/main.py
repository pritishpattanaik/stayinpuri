from contextlib import asynccontextmanager
import os
from pathlib import Path

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


# Mount static files - use absolute path based on deployment
# Get the directory containing this file (app/) and go up twice to reach puriguide/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
frontend_path = BASE_DIR / "frontend"

print(f"DEBUG: BASE_DIR = {BASE_DIR}")
print(f"DEBUG: frontend_path = {frontend_path}")
print(f"DEBUG: frontend exists = {frontend_path.exists()}")

if frontend_path.exists():
    # Mount asset directories
    css_path = frontend_path / "css"
    js_path = frontend_path / "js"
    images_path = frontend_path / "images"

    if css_path.exists():
        app.mount("/css", StaticFiles(directory=str(css_path)), name="css")
    if js_path.exists():
        app.mount("/js", StaticFiles(directory=str(js_path)), name="js")
    if images_path.exists():
        app.mount("/images", StaticFiles(directory=str(images_path)), name="images")

    # Catch-all route for HTML files
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve API docs first
        if full_path == "docs" or full_path == "openapi.json":
            return {"detail": "Use /api/health for API"}

        file_path = frontend_path / full_path

        # If it's a file, serve it
        if file_path.is_file():
            return FileResponse(file_path)

        # If requesting a directory path without trailing slash, try with .html
        if not full_path and (frontend_path / "index.html").is_file():
            return FileResponse(frontend_path / "index.html")

        # Try appending .html
        html_path = frontend_path / f"{full_path}.html"
        if html_path.is_file():
            return FileResponse(html_path)

        # Default to index.html for SPA-like behavior
        index_file = frontend_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        return Response("Not Found", status_code=404)
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
