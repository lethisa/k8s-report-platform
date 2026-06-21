import time
import psycopg2
import os

while True:

    try:

        psycopg2.connect(
            os.getenv("DATABASE_URL")
        )

        print("Database ready")
        break

    except Exception:

        print("Waiting database...")

        time.sleep(5)