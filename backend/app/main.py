from contextlib import asynccontextmanager

from fastapi import FastAPI
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
