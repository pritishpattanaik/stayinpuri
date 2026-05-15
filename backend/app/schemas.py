from datetime import datetime

from pydantic import BaseModel, Field


class PropertyResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    capacity: int
    bedrooms: int
    price_per_night: int
    amenities: str | None = None
    image_url: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ServiceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    price: int
    price_unit: str = "per day"
    icon: str | None = None
    image_url: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    service_type: str = Field(..., min_length=1)
    property_slug: str | None = None
    service_id: int | None = None
    guest_name: str = Field(..., min_length=2, max_length=100)
    guest_email: str | None = None
    guest_phone: str = Field(..., min_length=8, max_length=20)
    num_guests: int = Field(default=1, ge=1)
    checkin_date: str | None = None
    checkout_date: str | None = None
    special_requests: str | None = None


class BookingResponse(BaseModel):
    id: int
    booking_ref: str
    service_type: str
    property_slug: str | None = None
    guest_name: str
    guest_email: str | None = None
    guest_phone: str
    num_guests: int
    checkin_date: str | None = None
    checkout_date: str | None = None
    special_requests: str | None = None
    total_amount: float | None = None
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
