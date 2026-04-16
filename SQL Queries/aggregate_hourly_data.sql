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
 
    -- Count hours above 35°C — proxy for peak electricity demand days
    COUNT(*) FILTER (WHERE h.temperature_c > 35)          AS hours_above_35c
 
FROM weather_hourly h
GROUP BY
    h.city_id,
    DATE(h.observed_at AT TIME ZONE 'Australia/Sydney')