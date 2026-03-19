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
    assert body["characters"][0]["canonical_name"] == "MIA"
    assert body["validation"]["is_likely_screenplay"] is True


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
    assert body["validation"]["source_type"] == "txt"


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
    assert created["characters"][0]["canonical_name"] == "MIA"
    assert created["validation"]["is_likely_screenplay"] is True

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


def test_parse_rejects_non_screenplay_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/parse",
        json={"title": "Notes", "raw_text": "Quarterly revenue grew by 14 percent.\nPlease review the roadmap."},
    )

    assert response.status_code == 422
    body = response.json()
    assert "screenplay" in body["detail"]["message"].lower()
    assert body["detail"]["validation"]["is_likely_screenplay"] is False


def test_parse_file_rejects_pdf_for_now(client: TestClient) -> None:
    response = client.post(
        "/api/v1/parse-file",
        files={"script_file": ("script.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 415
    body = response.json()
    assert "txt" in body["detail"]["message"].lower()


def test_correction_persists_scene_heading_and_block_fields(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/scripts",
        json={
            "title": "Correction Test",
            "raw_text": "INT. ROOM - DAY\n\nMIA\nHello there.\n",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    scene = created["scenes"][0]
    dialogue_block = next(block for block in scene["elements"] if block["element_type"] == "dialogue")

    update_scene = client.post(
        f"/api/v1/scripts/{created['id']}/corrections",
        json={
            "target_type": "scene",
            "target_id": scene["scene_id"],
            "corrected_field": "heading",
            "new_value": "INT. ROOM - NIGHT",
        },
    )
    assert update_scene.status_code == 200
    updated_scene_body = update_scene.json()
    assert updated_scene_body["scenes"][0]["heading"] == "INT. ROOM - NIGHT"
    assert updated_scene_body["scenes"][0]["original_heading"] == "INT. ROOM - DAY"
    assert updated_scene_body["scenes"][0]["is_corrected"] is True

    update_block = client.post(
        f"/api/v1/scripts/{created['id']}/corrections",
        json={
            "target_type": "block",
            "target_id": dialogue_block["block_id"],
            "corrected_field": "text",
            "new_value": "Hello there, world.",
        },
    )
    assert update_block.status_code == 200
    updated_block_body = update_block.json()
    block = next(
        item
        for item in updated_block_body["scenes"][0]["elements"]
        if item["block_id"] == dialogue_block["block_id"]
    )
    assert block["text"] == "Hello there, world."
    assert block["original_text"] == "Hello there."
    assert block["is_corrected"] is True
    assert any(correction["corrected_field"] == "text" for correction in block["corrections"])

    fetch_response = client.get(f"/api/v1/scripts/{created['id']}")
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    fetched_block = next(
        item
        for item in fetched["scenes"][0]["elements"]
        if item["block_id"] == dialogue_block["block_id"]
    )
    assert fetched["scenes"][0]["heading"] == "INT. ROOM - NIGHT"
    assert fetched_block["text"] == "Hello there, world."
    assert len(fetched["corrections"]) == 2
    assert fetched["corrections"][0]["old_value"] == "INT. ROOM - DAY"


def test_correction_rejects_invalid_block_type(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/scripts",
        json={
            "title": "Invalid Correction Test",
            "raw_text": "INT. ROOM - DAY\n\nMIA\nHello.\n",
        },
    )
    created = create_response.json()
    block = created["scenes"][0]["elements"][1]

    response = client.post(
        f"/api/v1/scripts/{created['id']}/corrections",
        json={
            "target_type": "block",
            "target_id": block["block_id"],
            "corrected_field": "element_type",
            "new_value": "monologue",
        },
    )

    assert response.status_code == 400
    assert "invalid block type" in response.json()["detail"].lower()
