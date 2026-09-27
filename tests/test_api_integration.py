import importlib

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_people_simulation_feedback_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    monkeypatch.setenv("MODEL_BACKEND", "demo")
    monkeypatch.setenv("ENABLE_SIMULATION", "true")
    monkeypatch.setenv("API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    main = importlib.import_module("app.main")
    from app.db import get_db
    test_engine = create_engine(f"sqlite:///{(tmp_path / 'isolated.db').as_posix()}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(main, "settings", get_settings())
    def database():
        with Session(test_engine) as db:
            yield db
    main.app.dependency_overrides[get_db] = database
    monkeypatch.setattr(main.registry, "load", lambda: main.registry.current)
    headers = {"X-API-Key": "test-key"}
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/people").status_code == 401
        created = client.post(
            "/v1/people", headers=headers,
            json={"external_id": "INT-001", "display_name": "Integration User"},
        )
        assert created.status_code == 201
        person_id = created.json()["id"]
        observed = client.post(
            "/v1/simulation/observations", headers=headers,
            json={
                "person_id": person_id, "session_id": "integration-1",
                "face_score": 0.9, "voice_score": 0.8,
                "face_quality": 0.9, "voice_quality": 0.9,
            },
        )
        assert observed.status_code == 200
        assert observed.json()["decision"] == "allow"
        event_id = observed.json()["event_id"]
        feedback = client.put(
            f"/v1/events/{event_id}/feedback", headers=headers,
            json={"is_genuine": True, "reviewer": "pytest"},
        )
        assert feedback.status_code == 201
        assert client.get("/v1/events", headers=headers).json()[0]["id"] == event_id
    main.app.dependency_overrides.clear()
    test_engine.dispose()
    get_settings.cache_clear()
