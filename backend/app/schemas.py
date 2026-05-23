from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PropertyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    capacity: int
    bedrooms: int
    price_per_night: int
    amenities: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ServiceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    price: int
    price_unit: str = "per day"
    icon: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    service_type: str = Field(..., min_length=1)
    property_slug: Optional[str] = None
    service_id: Optional[int] = None
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_email: Optional[str] = None
    guest_phone: str = Field(..., min_length=8, max_length=20)
    num_guests: int = Field(default=1, ge=1)
    checkin_date: Optional[str] = None
    checkout_date: Optional[str] = None
    special_requests: Optional[str] = None


class BookingResponse(BaseModel):
    id: int
    booking_ref: str
    service_type: str
    property_slug: Optional[str] = None
    guest_name: str
    guest_email: Optional[str] = None
    guest_phone: str
    num_guests: int
    checkin_date: Optional[str] = None
    checkout_date: Optional[str] = None
    special_requests: Optional[str] = None
    total_amount: Optional[float] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SiteConfigResponse(BaseModel):
    site_name: str
    site_tagline: str
    site_phone: str
    site_email: str
    caretaker_phone: str
    caretaker_name: str
