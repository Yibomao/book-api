import os
import pathlib
import sys

import psycopg2
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Tests run against a real PostgreSQL instance, not a mock or an in-memory
# stand-in: the point of the migration was the database, so the database is
# what has to be exercised.
os.environ.setdefault(
    "DATABASE_URL", "postgresql://bookuser:bookpass@localhost:5432/booksdb"
)

import app as app_module  # noqa: E402
import init_db  # noqa: E402,F401  (importing it applies schema.sql)


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE books RESTART IDENTITY")
        conn.commit()
    with app_module.app.test_client() as c:
        yield c
