# STAGE 0 - Schema: create tables
import logging

# --- Logging ----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")

SCHEMA_SQL = """
-- Lookup: one row per city
CREATE TABLE IF NOT EXISTS cities (
    city_id    SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    state      TEXT NOT NULL,
    latitude   NUMERIC(7,4) NOT NULL,
    longitude  NUMERIC(7,4) NOT NULL
);
 
-- Raw layer: verbatim API response + content hash for change detection
-- Re-running the pipeline never creates duplicates (UNIQUE on city+time)
CREATE TABLE IF NOT EXISTS weather_raw (
    raw_id        BIGSERIAL PRIMARY KEY,
    city_id       INT NOT NULL REFERENCES cities(city_id),
    observed_at   TIMESTAMPTZ NOT NULL,
    content_hash  TEXT NOT NULL,
    payload       JSONB NOT NULL,
    ingested_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (city_id, observed_at)
);
 
-- Normalised hourly layer: typed columns
CREATE TABLE IF NOT EXISTS weather_hourly (
    hourly_id        BIGSERIAL PRIMARY KEY,
    city_id          INT NOT NULL REFERENCES cities(city_id),
    observed_at      TIMESTAMPTZ NOT NULL,
    temperature_c    NUMERIC(5,2),
    humidity_pct     NUMERIC(5,2),
    windspeed_kmh    NUMERIC(6,2),
    solar_rad_wm2    NUMERIC(8,2),
    precipitation_mm NUMERIC(6,2),
    UNIQUE (city_id, observed_at)
);
 
-- Daily aggregates: built by SQL from weather_hourly
CREATE TABLE IF NOT EXISTS weather_daily (
    daily_id          BIGSERIAL PRIMARY KEY,
    city_id           INT  NOT NULL REFERENCES cities(city_id),
    obs_date          DATE NOT NULL,
    avg_temp_c        NUMERIC(5,2),
    max_temp_c        NUMERIC(5,2),
    min_temp_c        NUMERIC(5,2),
    avg_humidity_pct  NUMERIC(5,2),
    total_rain_mm     NUMERIC(7,2),
    total_solar_wh_m2 NUMERIC(10,2),
    hours_above_35c   INT,
    UNIQUE (city_id, obs_date)
);
 
CREATE INDEX IF NOT EXISTS idx_hourly_city_time
    ON weather_hourly (city_id, observed_at DESC);
"""


def create_schema(conn) -> None:
    log.info("____ STAGE 0: Creating Schema ____________________")
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()
    log.info("Schema ready.")
