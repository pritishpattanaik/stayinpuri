from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Property
from app.schemas import PropertyResponse

router = APIRouter()


@router.get("/", response_model=list[PropertyResponse])
async def list_properties(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.is_active == True))
    return result.scalars().all()


@router.get("/{slug}", response_model=PropertyResponse)
async def get_property(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Property).where(Property.slug == slug))
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop
