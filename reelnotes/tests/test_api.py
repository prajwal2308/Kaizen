import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_store
from app.store import Store

from .conftest import API_KEY, make_note


@pytest.fixture
def client(settings, monkeypatch):
    store = Store(settings.db_path)
    started: list[tuple[str, str]] = []

    # The real pipeline downloads and transcribes; record the call instead.
    monkeypatch.setattr(
        "app.main.process",
        lambda note_id, url, _settings, _store: started.append((note_id, url)),
    )

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_store] = lambda: store
    test_client = TestClient(app)
    test_client.store = store
    test_client.started = started
    yield test_client
    app.dependency_overrides.clear()


def test_ingest_requires_the_key(client):
    assert client.post("/ingest", json={"url": "https://example.com/r/1"}).status_code == 401
    assert client.post(
        "/ingest",
        json={"url": "https://example.com/r/1"},
        headers={"X-API-Key": "wrong"},
    ).status_code == 401


def test_ingest_returns_immediately_and_queues_the_work(client):
    response = client.post(
        "/ingest",
        json={"url": "https://www.instagram.com/reel/ABC/"},
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 202
    note_id = response.json()["id"]
    assert response.json()["status"] == "pending"
    assert client.started == [(note_id, "https://www.instagram.com/reel/ABC/")]


def test_shared_text_around_the_url_is_tolerated(client):
    response = client.post(
        "/ingest",
        json={"url": "look at this https://www.facebook.com/share/r/abc/ 😀"},
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 202
    assert client.started[0][1] == "https://www.facebook.com/share/r/abc/"


def test_text_with_no_url_is_rejected(client):
    response = client.post(
        "/ingest", json={"url": "no link here"}, headers={"X-API-Key": API_KEY}
    )

    assert response.status_code == 422


def test_browser_views_accept_the_key_as_a_query_param(client):
    note_id = client.store.create_pending("https://example.com/r/9")
    client.store.save_note(note_id, make_note(), transcript="fifty thirty twenty")

    assert client.get("/").status_code == 401

    listing = client.get("/", params={"k": API_KEY})
    assert listing.status_code == 200
    assert "The 50/30/20 budget rule" in listing.text

    page = client.get(f"/notes/{note_id}", params={"k": API_KEY})
    assert page.status_code == 200
    assert "Multiply by 0.5 for needs" in page.text
    assert "Savings share" in page.text


def test_search_narrows_the_listing(client):
    for note in (make_note(), make_note(title="Kyoto in November", category="travel")):
        note_id = client.store.create_pending("https://example.com/r/x")
        client.store.save_note(note_id, note, transcript="unrelated words")

    hits = client.get("/", params={"k": API_KEY, "q": "kyoto"})
    assert "Kyoto in November" in hits.text
    assert "The 50/30/20 budget rule" not in hits.text


def test_unknown_note_is_404(client):
    assert client.get("/notes/nope", params={"k": API_KEY}).status_code == 404
