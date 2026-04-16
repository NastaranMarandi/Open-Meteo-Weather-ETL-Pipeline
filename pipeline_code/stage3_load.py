# STAGE 3 — Load: upsert into PostgreSQL with change detection
import logging
import hashlib
import json
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")


def content_hash(row: dict) -> str:
    """
    SHA-256 of the row's numeric payload.
    If the API re-publishes the same observation with no changes,
    we detect it here and skip the write entirely.
    """
    payload = {k: row.get(k) for k in
               ["temperature_c", "humidity_pct", "windspeed_kmh",
                "solar_rad_wm2", "precipitation_mm"]}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def load(cities: list[dict], conn, raw_rows: list[dict], clean_rows: list[dict]) -> dict:
    log.info("___ STAGE 3: LOAD ____________________________")

    # Upsert cities and build a name → city_id map
    with conn.cursor() as cur:
        for city in cities:
            cur.execute("""
                INSERT INTO cities (name, state, latitude, longitude)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (city["name"], city["state"], city["lat"], city["lon"]))
        conn.commit()
        cur.execute("SELECT city_id, name FROM cities")
        city_map = {name: cid for cid, name in cur.fetchall()}

    inserted = updated = skipped = 0
    CHUNK_SIZE = 5000

    for start in range(0, len(raw_rows), CHUNK_SIZE):
        # untouched raw API rows
        raw_chunk = raw_rows[start: start + CHUNK_SIZE]
        # transformed rows
        clean_chunk = clean_rows[start: start + CHUNK_SIZE]

        # --- Raw layer (weather_raw table)
        raw_tuples = []
        for row in raw_chunk:
            cid = city_map[row["city"]]
            # Hash the full raw payload so we detect any upstream change
            chash = content_hash(row)
            payload = json.dumps(row)
            raw_tuples.append((cid, row["observed_at"], chash, payload))

        with conn.cursor() as cur:
            city_ids = [r[0] for r in raw_tuples]
            timestamps = [r[1] for r in raw_tuples]

            cur.execute("""
                SELECT city_id, observed_at::text, content_hash
                FROM weather_raw
                WHERE city_id         = ANY(%s)
                AND   observed_at::text = ANY(%s)
            """, (city_ids, timestamps))

            existing = {}
            for cid, ts, chash in cur.fetchall():
                existing[(cid, ts)] = chash

        to_insert = []
        # track what changed to gate weather_hourly writes
        changed_keys = set()

        with conn.cursor() as cur:
            for cid, ts, chash, payload in raw_tuples:
                prev = existing.get((cid, str(ts)))
                if prev is None:
                    to_insert.append((cid, ts, chash, payload))
                    # new row — needs hourly insert
                    changed_keys.add((cid, ts))
                    inserted += 1
                elif prev != chash:
                    cur.execute("""
                        UPDATE weather_raw
                        SET content_hash=%s, payload=%s, ingested_at=NOW()
                        WHERE city_id=%s AND observed_at=%s
                    """, (chash, payload, cid, ts))
                    changed_keys.add(
                        (cid, ts))   # changed row — needs hourly update
                    updated += 1
                else:
                    skipped += 1                  # unchanged data — skip hourly entirely

            if to_insert:
                execute_values(cur, """
                    INSERT INTO weather_raw
                        (city_id, observed_at, content_hash, payload)
                    VALUES %s
                    ON CONFLICT (city_id, observed_at) DO NOTHING
                """, to_insert)

        # --- Normalised hourly layer (weather_hourly) ---------------------
        # Only write rows that were new or changed in the raw layer
        hourly_tuples = [
            (
                city_map[r["city"]], r["observed_at"],
                r["temperature_c"],  r["humidity_pct"],
                r["windspeed_kmh"],  r["solar_rad_wm2"],
                r["precipitation_mm"],
            )
            for r in clean_chunk
            if (city_map[r["city"]], r["observed_at"]) in changed_keys
        ]

        if hourly_tuples:
            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO weather_hourly
                        (city_id, observed_at, temperature_c, humidity_pct,
                         windspeed_kmh, solar_rad_wm2, precipitation_mm)
                    VALUES %s
                    ON CONFLICT (city_id, observed_at) DO UPDATE SET
                        temperature_c    = EXCLUDED.temperature_c,
                        humidity_pct     = EXCLUDED.humidity_pct,
                        windspeed_kmh    = EXCLUDED.windspeed_kmh,
                        solar_rad_wm2    = EXCLUDED.solar_rad_wm2,
                        precipitation_mm = EXCLUDED.precipitation_mm
                """, hourly_tuples)

        conn.commit()
        log.info(f"  Chunk {start // CHUNK_SIZE + 1}: {len(raw_chunk):,} rows")

    log.info(
        f"Load complete - inserted:{inserted}  updated:{updated}  skipped:{skipped}")
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
