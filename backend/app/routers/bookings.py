from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Booking
from app.schemas import BookingCreate, BookingResponse
from app.config import settings

router = APIRouter()


@router.post("/", response_model=BookingResponse, status_code=201)
async def create_booking(booking_data: BookingCreate, db: AsyncSession = Depends(get_db)):
    booking = Booking(**booking_data.model_dump())

    if booking_data.service_type == "homestay" and booking_data.property_slug:
        from app.models import Property

        result = await db.execute(
            select(Property).where(Property.slug == booking_data.property_slug)
        )
        prop = result.scalar_one_or_none()
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        if booking_data.checkin_date and booking_data.checkout_date:
            from datetime import datetime

            checkin = datetime.strptime(booking_data.checkin_date, "%Y-%m-%d")
            checkout = datetime.strptime(booking_data.checkout_date, "%Y-%m-%d")
            nights = (checkout - checkin).days
            if nights > 0:
                booking.total_amount = float(nights * prop.price_per_night)

    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking


@router.get("/", response_model=List[BookingResponse])
async def list_bookings(
    status: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    query = select(Booking).order_by(Booking.created_at.desc())
    if status:
        query = query.where(Booking.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{booking_ref}", response_model=BookingResponse)
async def get_booking(booking_ref: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Booking).where(Booking.booking_ref == booking_ref)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
