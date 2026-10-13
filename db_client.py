"""Small, parameterized PostGIS data-access layer."""

from sqlalchemy import create_engine, text

try:
    from .config import database_url
except ImportError:  # Supports direct execution from this directory.
    from config import database_url


class PostGISClient:
    def __init__(self, url=None):
        self.engine = create_engine(url or database_url(), pool_pre_ping=True)
        with self.engine.begin() as connection:
            connection.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_aqi_stations_station_time
                ON aqi_stations (station_name, recorded_at)
            """))
            connection.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_wildfire_hotspots_location_time
                ON wildfire_hotspots (latitude, longitude, acq_timestamp)
            """))

    def save_spatial_data(self, city_data: dict | None = None, hotspots: list[dict] | None = None) -> None:
        """Insert one city observation and hotspot vectors in one transaction."""
        with self.engine.begin() as connection:
            if city_data:
                connection.execute(text("""
                    INSERT INTO aqi_stations
                    (station_name, latitude, longitude, pm2_5, aqi_level,
                     wind_speed, wind_direction, recorded_at, geom)
                    VALUES (:city, :lat, :lon, :pm25, :aqi, :wind_speed,
                            :wind_direction, :recorded_at,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    ON CONFLICT (station_name, recorded_at) DO UPDATE SET
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        pm2_5 = EXCLUDED.pm2_5,
                        aqi_level = EXCLUDED.aqi_level,
                        wind_speed = EXCLUDED.wind_speed,
                        wind_direction = EXCLUDED.wind_direction,
                        geom = EXCLUDED.geom
                """), city_data)
            for hotspot in hotspots or []:
                connection.execute(text("""
                    INSERT INTO wildfire_hotspots
                    (latitude, longitude, brightness, acq_timestamp, confidence, geom)
                    VALUES (:lat, :lon, :brightness, :acq_timestamp, :confidence,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    ON CONFLICT (latitude, longitude, acq_timestamp) DO UPDATE SET
                        brightness = EXCLUDED.brightness,
                        confidence = EXCLUDED.confidence,
                        geom = EXCLUDED.geom
                """), hotspot)

    def get_latest_city_data(self, city_name: str) -> dict:
        """Return the latest AQI record and nearby wildfire count for a city."""
        with self.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT a.station_name AS city, a.latitude, a.longitude,
                       a.pm2_5, a.aqi_level, a.wind_speed, a.wind_direction,
                       a.recorded_at,
                       (SELECT count(*) FROM wildfire_hotspots w
                        WHERE ST_DWithin(
                            w.geom::geography,
                            ST_SetSRID(ST_MakePoint(a.longitude, a.latitude), 4326)::geography,
                            100000)) AS nearby_wildfires
                FROM aqi_stations a
                WHERE a.station_name = :city
                ORDER BY a.recorded_at DESC
                LIMIT 1
            """), {"city": city_name}).mappings().first()
        return dict(result) if result else {}
