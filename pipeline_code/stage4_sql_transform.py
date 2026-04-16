# STAGE 4 - SQL Transform: aggregate hourly → daily summary table
import logging
# ---logging ------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")

DAILY_SUMMARY_SQL = """
INSERT INTO weather_daily (
    city_id, obs_date,
    avg_temp_c, max_temp_c, min_temp_c,
    avg_humidity_pct, total_rain_mm,
    total_solar_wh_m2, hours_above_35c
)
SELECT
    h.city_id,
    -- Convert UTC storage back to local date for grouping
    DATE(h.observed_at AT TIME ZONE 'Australia/Sydney')   AS obs_date,
    ROUND(AVG(h.temperature_c)::numeric,    2)            AS avg_temp_c,
    ROUND(MAX(h.temperature_c)::numeric,    2)            AS max_temp_c,
    ROUND(MIN(h.temperature_c)::numeric,    2)            AS min_temp_c,
    ROUND(AVG(h.humidity_pct)::numeric,     2)            AS avg_humidity_pct,
    ROUND(SUM(h.precipitation_mm)::numeric, 2)            AS total_rain_mm,
 
    -- Sum of hourly W/m² ≈ Wh/m² — useful for solar generation estimates
    ROUND(SUM(h.solar_rad_wm2)::numeric,    2)            AS total_solar_wh_m2,
 
    -- Count hours above 35°C — useful for peak electricity demand days
    COUNT(*) FILTER (WHERE h.temperature_c > 35)          AS hours_above_35c
 
FROM weather_hourly h
GROUP BY
    h.city_id,
    DATE(h.observed_at AT TIME ZONE 'Australia/Sydney')
 
-- Update in place if data already exists for that day
ON CONFLICT (city_id, obs_date) DO UPDATE SET
    avg_temp_c        = EXCLUDED.avg_temp_c,
    max_temp_c        = EXCLUDED.max_temp_c,
    min_temp_c        = EXCLUDED.min_temp_c,
    avg_humidity_pct  = EXCLUDED.avg_humidity_pct,
    total_rain_mm     = EXCLUDED.total_rain_mm,
    total_solar_wh_m2 = EXCLUDED.total_solar_wh_m2,
    hours_above_35c   = EXCLUDED.hours_above_35c;
"""


def sql_transform(conn) -> None:
    log.info("--- STAGE 4: SQL TRANSFORM (hourly → daily) -----")
    with conn.cursor() as cur:
        cur.execute(DAILY_SUMMARY_SQL)
        log.info(f"{cur.rowcount} daily rows upserted")
    conn.commit()
