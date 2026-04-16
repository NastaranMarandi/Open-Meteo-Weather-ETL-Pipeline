# STAGE 1 - Extract: call Open-Meteo API per city and Return a flat list of dicts — one per hour — with city name attached.
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")


def extract_city(city: dict, date_from: str, date_to: str, base_url: str) -> list[dict]:

    params = {
        "latitude":        city["lat"],
        "longitude":       city["lon"],
        "start_date":      date_from,
        "end_date":        date_to,
        "hourly":          "temperature_2m,relativehumidity_2m,"
                           "windspeed_10m,shortwave_radiation,precipitation",
        "timezone":        "Australia/Sydney",
        "wind_speed_unit": "kmh",
    }

    log.info(f"Fetching {city['name']} ({date_from} to {date_to}) ...")
    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()["hourly"]

    rows = []
    for i, timestamp in enumerate(data["time"]):
        rows.append({
            "city":            city["name"],
            "observed_at":     timestamp,
            "temperature_c":   data["temperature_2m"][i],
            "humidity_pct":    data["relativehumidity_2m"][i],
            "windspeed_kmh":   data["windspeed_10m"][i],
            "solar_rad_wm2":   data["shortwave_radiation"][i],
            "precipitation_mm": data["precipitation"][i],
        })

    log.info(f"  → {len(rows):,} hourly rows for {city['name']}")
    return rows


def extract_all(cities: list[dict], date_from: str, date_to: str, base_url: str) -> list[dict]:
    log.info("____ STAGE 1: EXTRACT ____________________")
    all_rows = []

    for city in cities:
        all_rows.extend(extract_city(city, date_from, date_to, base_url))

    log.info(f"Total extracted: {len(all_rows):,} rows")
    return all_rows
