import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def main() -> None:
    """Simple script to verify PostgreSQL connection."""
    host = os.environ.get("PGHOST", "").strip()
    user = os.environ.get("PGUSER", "").strip()
    password = os.environ.get("PGPASSWORD", "").strip()
    dbname = os.environ.get("PGDATABASE", "postgres").strip()
    port = os.environ.get("PGPORT", "5432").strip()

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            sslmode="require",
        )

        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print("✅ Connected to Postgres")
            print("Postgres version:", version)

        conn.close()
    except Exception as exc:
        print("❌ Connection failed:")
        print(exc)


if __name__ == "__main__":
    main()

