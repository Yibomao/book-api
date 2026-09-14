CREATE TABLE IF NOT EXISTS books (
    id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title  text NOT NULL,
    author text NOT NULL
);

CREATE INDEX IF NOT EXISTS books_author_idx ON books (author);
