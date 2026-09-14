\# book-api



A small REST API for managing a book collection, built with Flask and SQLite.



Written to practice backend fundamentals: resource-oriented routing, request

validation, parameterized SQL, and per-request database connection handling.



\## Running it



Requires Python 3.10+.



```bash

pip install flask

python app.py

```



The server starts on `http://127.0.0.1:5000`. The SQLite database (`books.db`)

is created automatically on first run.



\## Endpoints



| Method | Path          | Description    | Success | Errors |

|--------|---------------|----------------|---------|--------|

| GET    | `/books`      | List all books | 200     | —      |

| GET    | `/books/<id>` | Fetch one book | 200     | 404    |

| POST   | `/books`      | Create a book  | 201     | 400    |

| DELETE | `/books/<id>` | Delete a book  | 204     | 404    |



Example:



```bash

curl -X POST http://127.0.0.1:5000/books \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"title": "Dune", "author": "Herbert"}'

```



\## Design notes



\*\*Parameterized queries.\*\* All SQL uses `?` placeholders with values passed

separately, never string interpolation. This is what prevents SQL injection —

an interpolated `WHERE id = {user\_input}` would let a caller pass `1 OR 1=1`

and read the entire table.



\*\*One connection per request.\*\* `get\_db()` opens a connection lazily and stores

it on Flask's request context `g`; `teardown\_appcontext` closes it when the

request ends. Opening a connection per query wastes work; never closing them

leaks handles until the database refuses new ones.



\*\*Validate before use.\*\* `POST /books` checks that `title` and `author` are

present and returns `400 Bad Request` if not, instead of raising a `KeyError`

and returning a 500. Client mistakes should produce client errors.



\*\*Runtime data stays out of version control.\*\* `books.db` is in `.gitignore` —

it is data, not source. A fresh clone creates its own empty database.



\## Roadmap



\- \[ ] `PUT /books/<id>` for updates

\- \[ ] Migrate from SQLite to PostgreSQL

\- \[ ] Containerize with Docker

\- \[ ] Deploy to a public URL

