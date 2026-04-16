# STAGE 5 — Report: print an analytical summary to console
import logging
# ---logging ------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("weather.etl")

REPORT_SQL = """
SELECT
    c.name                                                AS city,
    TO_CHAR(DATE_TRUNC('month', d.obs_date), 'YYYY-MM')  AS month,
    ROUND(AVG(d.avg_temp_c), 1)                           AS avg_temp_c,
    ROUND(MAX(d.max_temp_c), 1)                           AS hottest_day_c,
    ROUND(SUM(d.total_rain_mm), 0)                        AS rain_mm,
    SUM(d.hours_above_35c)                                AS extreme_heat_hrs
FROM weather_daily d
JOIN cities c USING (city_id)
WHERE d.obs_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months'
GROUP BY c.name, DATE_TRUNC('month', d.obs_date)
ORDER BY c.name, month;
"""


def report(conn) -> None:
    log.info("___ STAGE 5: REPORT ______________________________")
    with conn.cursor() as cur:
        cur.execute(REPORT_SQL)
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

    if not rows:
        log.warning("No rows returned — check data loaded correctly.")
        return

    # Pretty-print table
    col_w = [max(len(c), max(len(str(r[i])) for r in rows))
             for i, c in enumerate(col_names)]
    header = "  ".join(c.ljust(col_w[i]) for i, c in enumerate(col_names))
    divider = "  ".join("-" * w for w in col_w)

    print(f"\n{'─' * 65}")
    print("  Monthly Weather Summary — last 3 months")
    print(f"{'─' * 65}")
    print(header)
    print(divider)
    for row in rows:
        print("  ".join(str(v).ljust(col_w[i]) for i, v in enumerate(row)))

    # ASCII bar chart — average temperature by city
    from collections import defaultdict
    by_city = defaultdict(list)
    for row in rows:
        by_city[row[0]].append(float(row[2]))

    print(f"\n  Avg temperature by city (recent months)")
    print(f"  {'─' * 38}")
    for city, temps in sorted(by_city.items()):
        avg = sum(temps) / len(temps)
        bar = "█" * int(avg)
        print(f"  {city:<12}  {avg:>5.1f}°C  {bar}")
    print()
