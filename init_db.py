"""Apply schema.sql. Run before starting the server, not from inside it —
with several gunicorn workers, having each one try to create the table is a
race waiting to happen."""

import os
import pathlib
import sys

import psycopg2

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set")

schema = (pathlib.Path(__file__).parent / "schema.sql").read_text()

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(schema)

print("schema applied")
