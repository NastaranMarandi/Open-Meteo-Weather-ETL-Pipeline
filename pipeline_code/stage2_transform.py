# STAGE 2 - Transform: validate, clamp, type-cast
# Import pyhton packges
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")

BOUNDS = {
    "temperature_c":    (-20.0,  60.0),
    "humidity_pct":     (0.0, 100.0),
    "windspeed_kmh":    (0.0, 300.0),
    "solar_rad_wm2":    (0.0, 1500.0),
    "precipitation_mm": (0.0, 500.0),
}


def transform(rows: list[dict]) -> tuple[list[dict], list[dict]]:

    log.info("__ STAGE 2: TRANSFORM __________________")
    clean, rejected = [], []

    for row in rows:
        # Temperature is required - Drop if temperature is missing
        if row.get("temperature_c") is None:
            rejected.append({"row": row, "reason": "null temperature"})
            continue

        # Clamp all numeric fields and round
        for field, (lo, hi) in BOUNDS.items():
            val = row.get(field)
            if val is not None:
                row[field] = round(max(lo, min(hi, float(val))), 2)

        clean.append(row)

    log.info(f"Clean rows: {len(clean):,}  |  Rejected: {len(rejected):,}")
    # Return (clean_rows, rejected_rows)
    return clean, rejected
