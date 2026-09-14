import sqlite3
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DB_PATH = "books.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            title  TEXT NOT NULL,
            author TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


@app.get("/books")
def list_books():
    rows = get_db().execute("SELECT id, title, author FROM books").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/books/<int:book_id>")
def get_book(book_id):
    row = get_db().execute(
        "SELECT id, title, author FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.post("/books")
def create_book():
    data = request.get_json()
    if not data or "title" not in data or "author" not in data:
        return jsonify({"error": "title and author are required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO books (title, author) VALUES (?, ?)",
        (data["title"], data["author"]),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid, **data}), 201


@app.delete("/books/<int:book_id>")
def delete_book(book_id):
    db = get_db()
    cur = db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return "", 204


if __name__ == "__main__":
    init_db()
    app.run(debug=True)