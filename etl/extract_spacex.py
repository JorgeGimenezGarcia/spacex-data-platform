import os
import requests
import psycopg2
from datetime import datetime
from psycopg2.extras import execute_values

# Read DB connection info from environment variables
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DATABASE = os.getenv('PG_DATABASE', 'spacexdb')
PG_USER = os.getenv('PG_USER', 'admin')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'postgres_pass')

SPACE_X_API = 'https://api.spacexdata.com/v5/launches'


def fetch_launches():
    response = requests.get(SPACE_X_API)
    response.raise_for_status()
    return response.json()


def transform_records(launches):
    records = []
    for launch in launches:
        date_utc = launch.get('date_utc')
        if not date_utc:
            continue
        # Convert to datetime; remove trailing 'Z' if present
        try:
            launch_date = datetime.fromisoformat(date_utc.replace('Z', '+00:00'))
        except Exception:
            continue
        for core in launch.get('cores', []):
            core_id = core.get('core')
            flight = core.get('flight')
            reused = core.get('reused')
            if core_id is None:
                continue
            records.append((core_id, flight, reused, launch_date))
    return records


def load_records(records):
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )
    cursor = conn.cursor()
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS core_usage (
            core_id TEXT,
            flight INTEGER,
            reused BOOLEAN,
            launch_date TIMESTAMP
        );
    ''')
    # Bulk insert
    if records:
        execute_values(
            cursor,
            "INSERT INTO core_usage(core_id, flight, reused, launch_date) VALUES %s",
            records
        )
    conn.commit()
    cursor.close()
    conn.close()


def main():
    print("Fetching SpaceX launches...")
    launches = fetch_launches()
    print(f"Fetched {len(launches)} launches")
    records = transform_records(launches)
    print(f"Prepared {len(records)} core usage records")
    load_records(records)
    print("Load complete.")


if __name__ == '__main__':
    main()