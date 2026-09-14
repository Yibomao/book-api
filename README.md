# book-api

A REST API for managing a book collection - Flask, PostgreSQL, Docker.

**Live:** https://book-api-uttz.onrender.com - try [`/books`](https://book-api-uttz.onrender.com/books) or [`/health`](https://book-api-uttz.onrender.com/health)
*(free tier: the first request after a period of inactivity takes ~30s to wake the instance)*

Written to practice backend fundamentals end to end: resource-oriented routing,
request validation, parameterized SQL, connection pooling, containerization, and
deployment. It started on SQLite and was migrated to PostgreSQL - the notes below
record what that change actually required.

## Running it

With Docker (nothing to install but Docker itself):

```bash
docker compose up --build
```

The API is on `http://localhost:8000` and PostgreSQL on `localhost:5432`. The
schema is applied automatically on startup.

Without Docker, against a local PostgreSQL:

```bash
cp .env.example .env          # edit DATABASE_URL if yours differs
pip install -r requirements.txt
python init_db.py
python app.py
```

## Tests

```bash
docker compose up -d db
DATABASE_URL=postgresql://bookuser:bookpass@localhost:5432/booksdb pytest -q
```

14 tests covering the CRUD paths, every error branch, the author filter, and a
SQL-injection attempt that should come back empty rather than dumping the table.
They run against a real PostgreSQL instance rather than a mock, because the
database behavior is the part worth testing.

## Endpoints

| Method | Path            | Description                   | Success | Errors   |
|--------|-----------------|-------------------------------|---------|----------|
| GET    | `/`             | Service and endpoint listing  | 200     | -        |
| GET    | `/health`       | Liveness + database check     | 200     | 503      |
| GET    | `/books`        | List books, `?author=` filter | 200     | -        |
| GET    | `/books/<id>`   | Fetch one book                | 200     | 404      |
| POST   | `/books`        | Create a book                 | 201     | 400      |
| PUT    | `/books/<id>`   | Replace a book                | 200     | 400, 404 |
| DELETE | `/books/<id>`   | Delete a book                 | 204     | 404      |

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{"title": "Dune", "author": "Frank Herbert"}'
```

## Design notes

**Parameterized queries.** All SQL passes values separately from the statement
(`%s` placeholders in psycopg2, `?` in the SQLite version), never string
interpolation. An interpolated `WHERE id = {user_input}` would let a caller pass
`1 OR 1=1` and read the whole table. The `?author=` filter is parameterized too:
only the *shape* of the query is chosen in Python, never the value.

**A connection pool, not a connection per request.** SQLite connections are
cheap - opening one per request was fine. A PostgreSQL connection costs a
server-side process and a TCP round trip, and the server has a hard connection
limit, so the app keeps a `SimpleConnectionPool` and borrows from it. The pool is
built lazily because each gunicorn worker is a separate process and needs its own.

**One transaction per request.** `teardown_appcontext` commits if the handler
returned normally, rolls back if it raised, and returns the connection to the
pool either way. A request that fails halfway through leaves nothing
half-written.

**Schema changes run before the server, not inside it.** `init_db.py` is a
separate step in the container's start command. With two gunicorn workers,
having each one race to `CREATE TABLE IF NOT EXISTS` on boot is a bug waiting for
a busy day.

**`RETURNING` instead of a second query.** PostgreSQL can hand back the inserted
or updated row from the same statement, so creating a book is one round trip
rather than an `INSERT` followed by a `SELECT` - and there is no window where
another transaction could change the row in between.

**JSON errors for a JSON API.** Flask's default 404 and 500 handlers return HTML
pages, which breaks any client that calls `.json()` on the response. They're
overridden to return the same error shape as every other response.

**Config comes from the environment.** `DATABASE_URL` and `PORT` are read from
env vars with no hardcoded fallback to a production value, which is what lets the
identical image run under Docker Compose locally and on a host that injects its
own database URL. `.env` is gitignored - connection strings contain credentials.

**The container doesn't run as root.** The image creates an unprivileged user and
switches to it, so a compromised process isn't also root inside the container.

## Deployment

Runs as a single container against any managed PostgreSQL instance. The deployed
copy uses [Neon](https://neon.com) for the database and [Render](https://render.com)
for the web service; the only configuration is `DATABASE_URL`.
