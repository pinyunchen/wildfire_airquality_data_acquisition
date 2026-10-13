"""HTTP clients for public spatial and weather data providers."""

from csv import DictReader
from datetime import date, timedelta
from io import StringIO

import requests

try:
    from .config import FIRMS_API_KEY
except ImportError:  # Supports direct execution from this directory.
    from config import FIRMS_API_KEY


class SpatialDataFetcher:
    def __init__(self, firms_api_key: str | None = FIRMS_API_KEY, timeout: int = 20):
        self.firms_api_key = firms_api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "wildfire-aqi-pipeline/1.0"})

    def fetch_firms_hotspots(
        self,
        bbox: str = "-140,45,-110,70",
        days: int = 1,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[dict]:
        """Fetch recent FIRMS vectors or an inclusive historical date range."""
        if not self.firms_api_key:
            raise RuntimeError("FIRMS_API_KEY is not configured")
        if (start_date is None) != (end_date is None):
            raise ValueError("Both start_date and end_date are required for a historical query")

        if start_date is None:
            if not 1 <= days <= 5:
                raise ValueError("FIRMS supports a recent day range from 1 to 5")
            chunks = [(days, None)]
        else:
            first_day = _as_date(start_date)
            last_day = _as_date(end_date)
            if first_day > last_day:
                raise ValueError("start_date must be on or before end_date")
            chunks = []
            next_day = first_day
            while next_day <= last_day:
                chunk_days = min(5, (last_day - next_day).days + 1)
                chunks.append((chunk_days, next_day))
                next_day += timedelta(days=chunk_days)

        rows = []
        for chunk_days, chunk_start in chunks:
            url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{self.firms_api_key}/VIIRS_SNPP_NRT/{bbox}/{chunk_days}"
            if chunk_start is not None:
                url = f"{url}/{chunk_start.isoformat()}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            rows.extend(DictReader(StringIO(response.text)))
        return rows

    def fetch_open_meteo_hourly(
        self,
        lat: float,
        lon: float,
        days: int = 1,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
    ) -> list[dict]:
        """Fetch hourly PM2.5, source AQI, and wind observations aligned by time."""
        if (start_date is None) != (end_date is None):
            raise ValueError("Both start_date and end_date are required for a historical query")
        if start_date is None and not 1 <= days <= 92:
            raise ValueError("days must be between 1 and 92")
        if start_date is not None:
            first_day = _as_date(start_date)
            last_day = _as_date(end_date)
            if first_day > last_day:
                raise ValueError("start_date must be on or before end_date")

        common_params = {"latitude": lat, "longitude": lon, "timezone": "GMT"}
        if start_date is None:
            time_params = {"past_days": days}
        else:
            time_params = {
                "start_date": first_day.isoformat(),
                "end_date": last_day.isoformat(),
            }

        weather_response = self.session.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                **common_params,
                **time_params,
                "hourly": "wind_speed_10m,wind_direction_10m",
            },
            timeout=self.timeout,
        )
        weather_response.raise_for_status()
        weather_hourly = weather_response.json().get("hourly", {})
        wind_by_time = {
            observed_at: (speed, direction)
            for observed_at, speed, direction in zip(
                weather_hourly.get("time", []),
                weather_hourly.get("wind_speed_10m", []),
                weather_hourly.get("wind_direction_10m", []),
            )
        }

        air_response = self.session.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={
                **common_params,
                **time_params,
                "hourly": "pm2_5,us_aqi",
            },
            timeout=self.timeout,
        )
        air_response.raise_for_status()
        air_hourly = air_response.json().get("hourly", {})
        records = []
        for index, observed_at in enumerate(air_hourly.get("time", [])):
            wind_speed, wind_direction = wind_by_time.get(observed_at, (None, None))
            pm25_values = air_hourly.get("pm2_5", [])
            aqi_values = air_hourly.get("us_aqi", [])
            records.append({
                "pm25": pm25_values[index] if index < len(pm25_values) else None,
                "aqi": aqi_values[index] if index < len(aqi_values) else None,
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "recorded_at": observed_at,
            })
        return records


def _as_date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)
