"""A small REST API for a book collection, backed by PostgreSQL."""

import os

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, g

try:  # optional: loads .env for local development, ignored in production
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env, or run with "
        "docker compose up, which sets it for you."
    )

# Connection pool. A PostgreSQL connection costs a server-side process and a
# TCP round trip, so opening one per request the way the SQLite version did
# would be wasteful. The pool is created lazily on first use because each
# gunicorn worker is a separate process and needs its own.
_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=int(os.environ.get("DB_POOL_MAX", "5")),
            dsn=DATABASE_URL,
            cursor_factory=RealDictCursor,
        )
    return _pool


def get_conn():
    """Borrow a connection for the duration of this request."""
    if "conn" not in g:
        g.conn = get_pool().getconn()
    return g.conn


@app.teardown_appcontext
def release_conn(exception):
    """One transaction per request: commit if the handler succeeded, roll back
    if it raised, and always return the connection to the pool."""
    conn = g.pop("conn", None)
    if conn is None:
        return
    try:
        if exception is None:
            conn.commit()
        else:
            conn.rollback()
    finally:
        get_pool().putconn(conn)


def query(sql, params=(), fetch=None):
    """Run a statement. fetch: None, "one", or "all"."""
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        return cur.rowcount


def validate_book(data):
    """Return an error message, or None if the payload is usable."""
    if not isinstance(data, dict):
        return "request body must be a JSON object"
    for field in ("title", "author"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"{field} is required and must be a non-empty string"
    return None


@app.get("/")
def index():
    return jsonify(
        {
            "service": "book-api",
            "source": "https://github.com/Yibomao/book-api",
            "endpoints": {
                "GET /books": "list books, optional ?author= filter",
                "GET /books/<id>": "fetch one book",
                "POST /books": "create a book",
                "PUT /books/<id>": "replace a book",
                "DELETE /books/<id>": "delete a book",
                "GET /health": "liveness and database check",
            },
        }
    )


@app.get("/health")
def health():
    try:
        query("SELECT 1", fetch="one")
    except psycopg2.Error:
        return jsonify({"status": "unhealthy", "database": "unreachable"}), 503
    return jsonify({"status": "ok", "database": "reachable"})


@app.get("/books")
def list_books():
    author = request.args.get("author")
    if author:
        # Still parameterized: the value is passed separately, only the shape
        # of the SQL is chosen in Python.
        rows = query(
            "SELECT id, title, author FROM books WHERE author ILIKE %s ORDER BY id",
            (f"%{author}%",),
            fetch="all",
        )
    else:
        rows = query("SELECT id, title, author FROM books ORDER BY id", fetch="all")
    return jsonify(rows)


@app.get("/books/<int:book_id>")
def get_book(book_id):
    row = query(
        "SELECT id, title, author FROM books WHERE id = %s", (book_id,), fetch="one"
    )
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@app.post("/books")
def create_book():
    data = request.get_json(silent=True)
    error = validate_book(data)
    if error:
        return jsonify({"error": error}), 400
    row = query(
        "INSERT INTO books (title, author) VALUES (%s, %s) RETURNING id, title, author",
        (data["title"].strip(), data["author"].strip()),
        fetch="one",
    )
    return jsonify(row), 201


@app.put("/books/<int:book_id>")
def update_book(book_id):
    data = request.get_json(silent=True)
    error = validate_book(data)
    if error:
        return jsonify({"error": error}), 400
    row = query(
        "UPDATE books SET title = %s, author = %s WHERE id = %s "
        "RETURNING id, title, author",
        (data["title"].strip(), data["author"].strip(), book_id),
        fetch="one",
    )
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(row)


@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    deleted = query("DELETE FROM books WHERE id = %s", (book_id,))
    if deleted == 0:
        return jsonify({"error": "not found"}), 404
    return "", 204


# Clients of a JSON API should get JSON back, including on errors — the default
# Flask handlers return HTML pages.
@app.errorhandler(404)
def handle_404(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def handle_405(_):
    return jsonify({"error": "method not allowed"}), 405


@app.errorhandler(500)
def handle_500(_):
    return jsonify({"error": "internal server error"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
