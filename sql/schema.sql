CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS aqi_stations (
    station_name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    pm2_5 DOUBLE PRECISION,
    aqi_level DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION,
    wind_direction DOUBLE PRECISION,
    recorded_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    geom geometry(Point, 4326) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_aqi_stations_station_time
    ON aqi_stations (station_name, recorded_at);

CREATE INDEX IF NOT EXISTS idx_aqi_stations_geom
    ON aqi_stations USING GIST (geom);

CREATE TABLE IF NOT EXISTS wildfire_hotspots (
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    brightness DOUBLE PRECISION,
    acq_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    confidence TEXT,
    geom geometry(Point, 4326) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_wildfire_hotspots_location_time
    ON wildfire_hotspots (latitude, longitude, acq_timestamp);

CREATE INDEX IF NOT EXISTS idx_wildfire_hotspots_geom
    ON wildfire_hotspots USING GIST (geom);
