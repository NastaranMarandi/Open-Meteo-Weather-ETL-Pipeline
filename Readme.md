## Description:
An ETL pipeline that ingests weather data from the Meteo API (a free, open-source API), processes it, and stores it in a PostgreSQL database using Docker and Python.

## Dependencies:
    pip install requests psycopg2-binary pandas
 
## Setup:
    1. Start Postgres via Docker:
       docker run --name weather-etl -e POSTGRES_USER=username -e POSTGRES_PASSWORD=password -e POSTGRES_DB=weather_etl -p port-No:port-No -d postgres:16
## Docker Start:
docker compose up -d