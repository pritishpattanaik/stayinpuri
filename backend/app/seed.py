from app.main import app
from app.database import engine, Base
from app.models import Property, Service
from app.config import settings

PROPERTIES = [
    {
        "name": "Asiyana",
        "slug": "asiyana",
        "description": "A beautiful and cozy homestay located near Puri beach. Perfect for families seeking a peaceful retreat with modern amenities and traditional Odia hospitality.",
        "capacity": 4,
        "bedrooms": 2,
        "price_per_night": 2500,
        "amenities": "WiFi, AC, Kitchen, Hot Water, Parking, TV",
        "image_url": "images/placeholders/asiyana-exterior.jpg",
        "is_active": True,
    },
    {
        "name": "Tulsi Vihar",
        "slug": "tulsi-vihar",
        "description": "A charming homestay close to the Jagannath Temple. Ideal for devotees and travelers who want to experience the spiritual heart of Puri.",
        "capacity": 3,
        "bedrooms": 2,
        "price_per_night": 2000,
        "amenities": "WiFi, AC, Hot Water, Parking",
        "image_url": "images/placeholders/tulsi-exterior.jpg",
        "is_active": True,
    },
]

SERVICES = [
    {
        "name": "Car Rental",
        "slug": "car-rental",
        "description": "AC cars with experienced local drivers. Day trips to Konark, Chilika Lake, Bhubaneswar and more.",
        "price": 1500,
        "price_unit": "per day",
        "icon": "fa-car",
        "image_url": "images/placeholders/car-rental.jpg",
        "is_active": True,
    },
    {
        "name": "Bike Rental",
        "slug": "bike-rental",
        "description": "Explore Puri at your own pace. Scooters and motorcycles available by the hour or day.",
        "price": 300,
        "price_unit": "per day",
        "icon": "fa-motorcycle",
        "image_url": "images/placeholders/bike-rental.jpg",
        "is_active": True,
    },
    {
        "name": "Airport Transfer",
        "slug": "airport-transfer",
        "description": "Pickup and drop from Bhubaneswar Airport (BBI). Comfortable AC vehicle. On time, every time.",
        "price": 1800,
        "price_unit": "per trip",
        "icon": "fa-plane",
        "image_url": "images/placeholders/airport-transfer.jpg",
        "is_active": True,
    },
    {
        "name": "Railway Station Transfer",
        "slug": "station-transfer",
        "description": "Pickup and drop from Puri Railway Station. Available 24/7.",
        "price": 300,
        "price_unit": "per trip",
        "icon": "fa-train",
        "image_url": "images/placeholders/airport-transfer.jpg",
        "is_active": True,
    },
    {
        "name": "Cricket Coaching",
        "slug": "cricket-coaching",
        "description": "Book a throw-down session with a professional coach at Sobers Sporting Academy. Nets available daily.",
        "price": 500,
        "price_unit": "per session",
        "icon": "fa-baseball-bat-ball",
        "image_url": "images/placeholders/cricket-coaching.jpg",
        "is_active": True,
    },
    {
        "name": "Guided Temple Tour",
        "slug": "temple-tour",
        "description": "Curated half-day and full-day tours to temples, markets, and heritage sites with knowledgeable local guides.",
        "price": 800,
        "price_unit": "per day",
        "icon": "fa-map-location-dot",
        "image_url": "images/placeholders/jagannath-temple.jpg",
        "is_active": True,
    },
]


async def seed_database():
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select

    async with AsyncSession(engine) as session:
        for prop_data in PROPERTIES:
            result = await session.execute(
                select(Property).where(Property.slug == prop_data["slug"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                prop = Property(**prop_data)
                session.add(prop)

        for svc_data in SERVICES:
            result = await session.execute(
                select(Service).where(Service.slug == svc_data["slug"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                svc = Service(**svc_data)
                session.add(svc)

        await session.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    import asyncio
    from app.database import init_db

    async def main():
        await init_db()
        await seed_database()

    asyncio.run(main())
