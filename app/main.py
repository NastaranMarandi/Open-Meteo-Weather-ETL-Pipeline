# Orchestrator — wire all stages together
# Import pyhton packges
from datetime import date, timedelta
import logging
import psycopg2

# Import Python files from pipeline_code folder
from pipeline_code.stage0_create_schema import create_schema
from pipeline_code.stage1_extract import extract_all
from pipeline_code.stage2_transform import transform
from pipeline_code.stage3_load import load
from pipeline_code.stage4_sql_transform import sql_transform
from pipeline_code.stage5_report import report

# ---logging ------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")

# ---config ---------------------------------------
DB_CONFIG = {
    "host":     "hostname",
    "port":     "port-No",
    "dbname":   "weather_etl",
    "user":     "username",
    "password": "password",
}

CITIES = [
    {"name": "Sydney",    "state": "NSW", "lat": -33.87, "lon": 151.21},
    {"name": "Melbourne", "state": "VIC", "lat": -37.81, "lon": 144.96},
    {"name": "Brisbane",  "state": "QLD", "lat": -27.47, "lon": 153.02},
    {"name": "Adelaide",  "state": "SA",  "lat": -34.93, "lon": 138.60},
    {"name": "Perth",     "state": "WA",  "lat": -31.95, "lon": 115.86},
]

DATE_FROM = "2025-01-01"
DATE_TO = str(date.today() - timedelta(days=1))

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def run_pipeline():
    log.info("=" * 50)
    log.info("  WEATHER ETL  |  Open-Meteo → PostgreSQL")
    log.info("=" * 50)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        create_schema(conn)
        raw_rows = extract_all(CITIES, DATE_FROM, DATE_TO, OPEN_METEO_URL)
        clean, _ = transform(raw_rows)
        load(CITIES, conn, raw_rows, clean)
        sql_transform(conn)
        report(conn)
    except Exception as e:
        log.error(f"Pipeline failed: {e}", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_pipeline()
