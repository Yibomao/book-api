def make_book(client, title="Dune", author="Herbert"):
    return client.post("/books", json={"title": title, "author": author})


def test_health_reports_database(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["database"] == "reachable"


def test_list_is_empty_initially(client):
    res = client.get("/books")
    assert res.status_code == 200
    assert res.get_json() == []


def test_create_returns_201_and_generated_id(client):
    res = make_book(client)
    assert res.status_code == 201
    body = res.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"


def test_created_book_is_readable(client):
    book_id = make_book(client).get_json()["id"]
    res = client.get(f"/books/{book_id}")
    assert res.status_code == 200
    assert res.get_json()["author"] == "Herbert"


def test_create_rejects_missing_fields(client):
    res = client.post("/books", json={"title": "Dune"})
    assert res.status_code == 400
    assert "author" in res.get_json()["error"]


def test_create_rejects_blank_strings(client):
    res = client.post("/books", json={"title": "   ", "author": "Herbert"})
    assert res.status_code == 400


def test_create_rejects_non_json_body(client):
    res = client.post("/books", data="not json", content_type="text/plain")
    assert res.status_code == 400


def test_update_replaces_fields(client):
    book_id = make_book(client).get_json()["id"]
    res = client.put(f"/books/{book_id}", json={"title": "Messiah", "author": "Herbert"})
    assert res.status_code == 200
    assert res.get_json()["title"] == "Messiah"
    assert client.get(f"/books/{book_id}").get_json()["title"] == "Messiah"


def test_update_missing_book_is_404(client):
    res = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert res.status_code == 404


def test_delete_removes_book(client):
    book_id = make_book(client).get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_is_404(client):
    assert client.delete("/books/9999").status_code == 404


def test_author_filter_matches_case_insensitively(client):
    make_book(client, "Dune", "Frank Herbert")
    make_book(client, "Neuromancer", "William Gibson")
    res = client.get("/books?author=herbert")
    assert res.status_code == 200
    titles = [b["title"] for b in res.get_json()]
    assert titles == ["Dune"]


def test_sql_injection_attempt_is_treated_as_data(client):
    make_book(client, "Dune", "Herbert")
    res = client.get("/books?author=%27%20OR%201%3D1%20--")
    assert res.status_code == 200
    # The payload is matched as a literal string, so it finds nothing rather
    # than returning every row.
    assert res.get_json() == []


def test_unknown_route_returns_json_not_html(client):
    res = client.get("/nope")
    assert res.status_code == 404
    assert res.is_json
