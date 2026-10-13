"""Independent GIS pipeline entry point."""

import argparse
from datetime import date

try:
    from .config import BC_CITIES
    from .db_client import PostGISClient
    from .fetcher import SpatialDataFetcher
except ImportError:  # Supports `python main.py` from this directory.
    from config import BC_CITIES
    from db_client import PostGISClient
    from fetcher import SpatialDataFetcher


def run(
    days: int = 1,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> None:
    if (start_date is None) != (end_date is None):
        raise ValueError("Both start_date and end_date are required")

    fetcher = SpatialDataFetcher()
    database = PostGISClient()
    hotspots = fetcher.fetch_firms_hotspots(
        days=days,
        start_date=start_date,
        end_date=end_date,
    )
    normalized_hotspots = [
        {
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "brightness": float(row["bright_ti4"]) if row.get("bright_ti4") else None,
            "acq_timestamp": f"{row.get('acq_date')} {str(row.get('acq_time', '0000')).zfill(4)[:2]}:{str(row.get('acq_time', '0000')).zfill(4)[2:]}:00",
            "confidence": row.get("confidence", "nominal"),
        }
        for row in hotspots
        if row.get("latitude") and row.get("longitude")
    ]
    database.save_spatial_data(hotspots=normalized_hotspots)
    stored_observations = 0
    for city, coordinates in BC_CITIES.items():
        observations = fetcher.fetch_open_meteo_hourly(
            lat=coordinates["latitude"],
            lon=coordinates["longitude"],
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        for observation in observations:
            city_data = {
                "city": city,
                "lat": coordinates["latitude"],
                "lon": coordinates["longitude"],
                **observation,
            }
            database.save_spatial_data(city_data=city_data)
            stored_observations += 1
    print(
        f"Stored {len(normalized_hotspots)} FIRMS hotspots and "
        f"{stored_observations} hourly AQI/weather observations."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch BC wildfire and weather data into PostGIS.")
    parser.add_argument("--days", type=int, default=None, choices=range(1, 6), help="Recent days to fetch (default: 1)")
    parser.add_argument("--start", help="Inclusive start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="Inclusive end date (YYYY-MM-DD)")
    args = parser.parse_args()
    if bool(args.start) != bool(args.end):
        parser.error("--start and --end must be provided together")
    if args.start and args.days is not None:
        parser.error("use either --days or --start/--end, not both")
    try:
        start = date.fromisoformat(args.start) if args.start else None
        end = date.fromisoformat(args.end) if args.end else None
    except ValueError as error:
        parser.error(str(error))
    run(days=args.days or 1, start_date=start, end_date=end)
