from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db
from app.db.base import Base
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_endpoint(client: TestClient) -> None:
    payload = {
        "title": "Sample Screenplay",
        "raw_text": "INT. ROOM - DAY\n\nMIA\nHello.\n",
    }

    response = client.post("/api/v1/parse", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["total_scenes"] == 1
    assert body["scenes"][0]["heading"] == "INT. ROOM - DAY"
    assert body["scenes"][0]["elements"][1]["speaker"] == "MIA"


def test_parse_file_endpoint(client: TestClient, fixture_dir: Path) -> None:
    script_path = fixture_dir / "sample_screenplay.txt"

    with script_path.open("rb") as file_handle:
        response = client.post(
            "/api/v1/parse-file",
            files={"script_file": ("sample_screenplay.txt", file_handle, "text/plain")},
            data={"title": "Uploaded Sample"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Uploaded Sample"
    assert body["total_scenes"] == 2


def test_create_list_and_fetch_stored_scripts(client: TestClient) -> None:
    payload = {
        "title": "Persisted Screenplay",
        "raw_text": "INT. ROOM - DAY\n\nMIA\nHello.\n",
    }

    create_response = client.post("/api/v1/scripts", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "Persisted Screenplay"
    assert created["raw_text"] == payload["raw_text"]
    assert created["total_scenes"] == 1

    list_response = client.get("/api/v1/scripts")
    assert list_response.status_code == 200
    scripts = list_response.json()
    assert len(scripts) == 1
    assert scripts[0]["id"] == created["id"]

    fetch_response = client.get(f"/api/v1/scripts/{created['id']}")
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert fetched["id"] == created["id"]
    assert fetched["scenes"][0]["heading"] == "INT. ROOM - DAY"


def test_create_script_from_file_persists_result(client: TestClient, fixture_dir: Path) -> None:
    script_path = fixture_dir / "sample_screenplay.txt"

    with script_path.open("rb") as file_handle:
        response = client.post(
            "/api/v1/scripts/file",
            files={"script_file": ("sample_screenplay.txt", file_handle, "text/plain")},
            data={"title": "Stored Upload"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Stored Upload"
    assert body["total_scenes"] == 2
    assert body["raw_text"].startswith("FADE IN:")
