"""Application configuration loaded from environment variables."""

from os import getenv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

DB_HOST = getenv("DB_HOST", "localhost")
DB_PORT = getenv("DB_PORT", "5432")
DB_NAME = getenv("DB_NAME", "wildfire_aqi")
DB_USER = getenv("DB_USER", "postgres")
DB_PASSWORD = getenv("DB_PASSWORD")
FIRMS_API_KEY = getenv("FIRMS_API_KEY")

AQI_LEVELS = {
    "Good": {"max": 28, "advice": "Air quality is satisfactory; enjoy normal outdoor activities."},
    "Moderate": {"min": 31, "max": 59, "advice": "Unusually sensitive people should consider reducing prolonged outdoor exertion."},
    "Sensitive": {"min": 60, "max": 89, "advice": "Sensitive groups should reduce prolonged or heavy outdoor exertion."},
    "Unhealthy": {"min": 90, "advice": "Everyone may experience effects; sensitive groups should avoid prolonged outdoor exertion."},
}

BC_CITIES = {
    "Vancouver": {"latitude": 49.2827, "longitude": -123.1207},
    "Kamloops": {"latitude": 50.6745, "longitude": -120.3273},
    "Kelowna": {"latitude": 49.8880, "longitude": -119.4960},
}


def database_url() -> str:
    """Return a SQLAlchemy URL without exposing the password in source code."""
    if not DB_PASSWORD:
        raise RuntimeError("DB_PASSWORD is not configured")
    from sqlalchemy.engine import URL

    return URL.create(
        "postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )
