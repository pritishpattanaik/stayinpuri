import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "PuriGuide")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "puriguide")
    DB_USER: str = os.getenv("DB_USER", "puriguide")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "puriguide123")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://puriguide:puriguide123@localhost:5432/puriguide",
    )

    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ]

    WHATSAPP_NUMBER: str = os.getenv("WHATSAPP_NUMBER", "")
    WHATSAPP_ENABLED: bool = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"

    BOOKING_REF_PREFIX: str = os.getenv("BOOKING_REF_PREFIX", "PG")
    BOOKING_CONFIRMATION_MESSAGE: str = os.getenv(
        "BOOKING_CONFIRMATION_MESSAGE",
        "Thank you for your booking! Our caretaker will contact you on WhatsApp within 2 hours.",
    )
    CARETAKER_PHONE: str = os.getenv("CARETAKER_PHONE", "")
    CARETAKER_NAME: str = os.getenv("CARETAKER_NAME", "Caretaker")

    PROPERTY_1_NAME: str = os.getenv("PROPERTY_1_NAME", "Asiyana")
    PROPERTY_1_SLUG: str = os.getenv("PROPERTY_1_SLUG", "asiyana")
    PROPERTY_1_CAPACITY: int = int(os.getenv("PROPERTY_1_CAPACITY", "4"))
    PROPERTY_1_PRICE: int = int(os.getenv("PROPERTY_1_PRICE", "2500"))
    PROPERTY_1_BEDROOMS: int = int(os.getenv("PROPERTY_1_BEDROOMS", "2"))

    PROPERTY_2_NAME: str = os.getenv("PROPERTY_2_NAME", "Tulsi Vihar")
    PROPERTY_2_SLUG: str = os.getenv("PROPERTY_2_SLUG", "tulsi-vihar")
    PROPERTY_2_CAPACITY: int = int(os.getenv("PROPERTY_2_CAPACITY", "3"))
    PROPERTY_2_PRICE: int = int(os.getenv("PROPERTY_2_PRICE", "2000"))
    PROPERTY_2_BEDROOMS: int = int(os.getenv("PROPERTY_2_BEDROOMS", "2"))

    SITE_NAME: str = os.getenv("SITE_NAME", "PuriGuide")
    SITE_TAGLINE: str = os.getenv("SITE_TAGLINE", "Your Complete Puri Travel Companion")
    SITE_CONTACT_EMAIL: str = os.getenv("SITE_CONTACT_EMAIL", "contact@puriguide.in")
    SITE_PHONE: str = os.getenv("SITE_PHONE", "+91XXXXXXXXXX")

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    @property
    def properties(self) -> list[dict]:
        return [
            {
                "name": self.PROPERTY_1_NAME,
                "slug": self.PROPERTY_1_SLUG,
                "capacity": self.PROPERTY_1_CAPACITY,
                "price": self.PROPERTY_1_PRICE,
                "bedrooms": self.PROPERTY_1_BEDROOMS,
            },
            {
                "name": self.PROPERTY_2_NAME,
                "slug": self.PROPERTY_2_SLUG,
                "capacity": self.PROPERTY_2_CAPACITY,
                "price": self.PROPERTY_2_PRICE,
                "bedrooms": self.PROPERTY_2_BEDROOMS,
            },
        ]


settings = Settings()
