from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Service
from app.schemas import ServiceResponse

router = APIRouter()


@router.get("/", response_model=list[ServiceResponse])
async def list_services(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.is_active == True))
    return result.scalars().all()


@router.get("/{slug}", response_model=ServiceResponse)
async def get_service(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.slug == slug))
    svc = result.scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    return svc
