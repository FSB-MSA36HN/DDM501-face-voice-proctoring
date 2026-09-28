import importlib
import json
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from app.config import get_settings
from app.db import get_db
from app.models import (
    BiometricSample,
    TenantKey,
    VerificationEvent,
    VerifySession,
    WebhookDelivery,
    utcnow,
)
from app.saas import derived_secret
from app.webhooks import deliver_one
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture
def saas(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY", "platform-test")
    monkeypatch.setenv("MODEL_BACKEND", "demo")
    monkeypatch.setenv("WEBHOOK_ALLOWED_HOSTS", "legacy-demo,localhost")
    monkeypatch.setenv("ENABLE_SIMULATION", "true")
    get_settings.cache_clear()
    main = importlib.import_module("app.main")
    engine = create_engine(f"sqlite:///{(tmp_path / 'saas.db').as_posix()}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main, "settings", get_settings())
    monkeypatch.setattr(main.registry, "load", lambda: main.registry.current)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db

    main.app.dependency_overrides[get_db] = database

    async def verify(person_id, session_id, face, voice, db, principal):
        accepted = (await face.read()) != b"impostor"
        event = VerificationEvent(person_id=person_id, session_id=session_id, accepted=accepted,
                                  risk_score=0.1 if accepted else 0.9, face_score=0.9, voice_score=0.8,
                                  face_quality=0.8, voice_quality=0.8, reasons=[], model_version="test-version", latency_ms=5)
        db.add(event)
        db.flush()
        return SimpleNamespace(event_id=event.id, decision="allow" if accepted else "review", accepted=accepted)

    monkeypatch.setattr(main.app.state, "perform_verification", verify)
    with TestClient(main.app) as client:
        yield client, engine, tmp_path
    main.app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


PLATFORM = {"X-API-Key": "platform-test"}


def tenant(client, name):
    response = client.post("/v1/admin/tenants", headers=PLATFORM, json={
        "name": name, "webhook_url": "http://legacy-demo:8000/webhooks/verification", "return_url": "http://localhost:18600/",
    })
    assert response.status_code == 201, response.text
    row = response.json()
    for role in ("operator", "integration"):
        key = client.post(f"/v1/admin/tenants/{row['id']}/keys", headers=PLATFORM, json={"role": role}).json()
        row[role] = {"X-API-Key": key["api_key"]}
        row[role + "_id"] = key["id"]
    return row


def person(client, engine, owner):
    created = client.post("/v1/people", headers=owner["operator"], json={"external_id": "CANDIDATE-1", "display_name": "Test Candidate"})
    assert created.status_code == 201, created.text
    row = created.json()
    with Session(engine) as db:
        for modality in ("face", "voice"):
            for index in range(2):
                db.add(BiometricSample(person_id=row["id"], modality=modality, embedding=[0.1] * 16,
                                       quality=0.9, sha256=f"test-{modality}-{index}"))
        db.commit()
    return row


def new_session(client, owner, person_id, request_id="request-1"):
    response = client.post("/v1/sessions", headers=owner["integration"], json={
        "person_id": person_id, "exam_id": "EXAM-1", "request_id": request_id,
    })
    assert response.status_code == 201, response.text
    return response.json()


def submit(client, row, face=b"genuine", consent="true"):
    params = parse_qs(urlsplit(row["verify_url"]).fragment)
    return client.post(f"/v1/public/sessions/{row['id']}/verify",
                       headers={"Authorization": "Bearer " + params["token"][0]}, data={"consent": consent},
                       files={"face_file": ("face.jpg", face, "image/jpeg"), "voice_file": ("voice.wav", b"wav", "audio/wav")})


def test_tenant_isolation_roles_and_revocation(saas):
    client, engine, _ = saas
    first, second = tenant(client, "First"), tenant(client, "Second")
    p1, p2 = person(client, engine, first), person(client, engine, second)
    assert p1["external_id"] == p2["external_id"]  # scoped identifiers, no global collisions
    assert client.get("/v1/people", headers=first["operator"]).json()[0]["id"] == p1["id"]
    assert client.post(f"/v1/people/{p1['id']}/enroll", headers=second["operator"]).status_code == 404
    assert client.post("/v1/verify", headers=second["operator"], data={"person_id": p1["id"], "session_id": "x"}).status_code == 404
    assert client.get("/v1/admin/tenants", headers=first["operator"]).status_code == 403
    assert client.post("/v1/admin/reload-model", headers=first["integration"]).status_code == 403
    assert client.post("/v1/verify", headers=first["integration"], data={"person_id": p1["id"], "session_id": "x"}).status_code == 403
    assert client.get("/v1/admin/reports/model-performance", headers=first["operator"]).status_code == 403
    key_id = first["integration_id"]
    with Session(engine) as db:
        key = db.get(TenantKey, key_id)
        assert key.digest != first["integration"]["X-API-Key"]
    assert client.delete(f"/v1/admin/keys/{key_id}", headers=PLATFORM).status_code == 200
    assert client.get("/v1/me", headers=first["integration"]).status_code == 401


def test_session_expiry_consent_replay_idempotency_and_cross_tenant(saas):
    client, engine, _ = saas
    first, second = tenant(client, "First"), tenant(client, "Second")
    candidate = person(client, engine, first)
    row = new_session(client, first, candidate["id"])
    duplicate = new_session(client, first, candidate["id"])
    assert row["id"] == duplicate["id"] and row["verify_url"] == duplicate["verify_url"]
    assert client.get(f"/v1/sessions/{row['id']}", headers=second["integration"]).status_code == 404
    assert client.get(f"/v1/public/sessions/{row['id']}").status_code == 401
    assert submit(client, row, consent="false").status_code == 422
    assert submit(client, row).json()["status"] == "allow"
    assert submit(client, row).status_code == 409
    event = client.get("/v1/events", headers=first["operator"]).json()[0]
    assert client.get("/v1/events", headers=second["operator"]).json() == []
    assert client.put(f"/v1/events/{event['id']}/feedback", headers=second["operator"],
                      json={"is_genuine": True, "reviewer": "test"}).status_code == 404
    with Session(engine) as db:
        assert db.scalar(select(VerifySession)).consent_at is not None
        assert db.scalar(select(WebhookDelivery)).status == "pending"
    expired = new_session(client, first, candidate["id"], "expired")
    with Session(engine) as db:
        db.get(VerifySession, expired["id"]).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert submit(client, expired).status_code == 410
    assert client.get(f"/v1/sessions/{expired['id']}", headers=first["operator"]).json()["status"] == "expired"


def test_manual_review_does_not_rewrite_prediction_and_queues_second_event(saas):
    client, engine, _ = saas
    owner = tenant(client, "Review organization")
    candidate = person(client, engine, owner)
    row = new_session(client, owner, candidate["id"])
    assert submit(client, row, face=b"impostor").json()["status"] == "review"
    body = {"approved": True, "notes": "Reviewed original evidence manually"}
    assert client.post(f"/v1/sessions/{row['id']}/review", headers=owner["integration"], json=body).status_code == 403
    result = client.post(f"/v1/sessions/{row['id']}/review", headers=owner["operator"], json=body)
    assert result.json()["status"] == "allow" and result.json()["sequence"] == 2
    assert client.post(f"/v1/sessions/{row['id']}/review", headers=owner["operator"], json=body).status_code == 409
    with Session(engine) as db:
        assert db.scalar(select(VerificationEvent)).accepted is False
        assert len(db.scalars(select(WebhookDelivery)).all()) == 2
    assert len(client.get("/v1/audit", headers=owner["operator"]).json()) >= 4


def test_webhook_retry_and_legacy_signature_replay_protection(saas, monkeypatch):
    client, engine, folder = saas
    owner = tenant(client, "Webhook organization")
    candidate = person(client, engine, owner)
    row = new_session(client, owner, candidate["id"])
    submit(client, row)
    legacy = importlib.import_module("legacy_demo.app")
    path = folder / "config.json"
    path.write_text(json.dumps({"tenant_id": owner["id"], "integration_key": owner["integration"]["X-API-Key"],
                                "webhook_secret": derived_secret("webhook", owner["id"])}))
    monkeypatch.setattr(legacy, "CONFIG", path)
    monkeypatch.setattr(legacy, "DATABASE", str(folder / "legacy.db"))
    with Session(engine, expire_on_commit=False) as db:
        assert deliver_one(db, post=lambda *_a, **_k: SimpleNamespace(status_code=503))
        delivery = db.scalar(select(WebhookDelivery))
        assert delivery.status == "pending" and delivery.attempts == 1
        delivery.next_attempt_at = utcnow() - timedelta(seconds=1)
        db.commit()
        with TestClient(legacy.app) as receiver:
            def post(url, data, headers, **kwargs):
                response = receiver.post("/webhooks/verification", content=data, headers=headers)
                assert response.status_code == 200
                assert receiver.post("/webhooks/verification", content=data, headers=headers).json()["duplicate"]
                assert receiver.post("/webhooks/verification", content=data + b" ", headers=headers).status_code == 401
                assert receiver.post("/webhooks/verification", content=data, headers={**headers, "X-Webhook-Timestamp": "0"}).status_code == 401
                return response
            assert deliver_one(db, post=post)
        assert delivery.status == "delivered" and delivery.attempts == 2


def test_callback_allowlist_blocks_arbitrary_networks(saas):
    client, _, _ = saas
    for url in ("http://169.254.169.254/latest", "http://localhost@evil.example/hook", "file:///etc/passwd"):
        response = client.post("/v1/admin/tenants", headers=PLATFORM, json={"name": "Blocked " + url, "webhook_url": url})
        assert response.status_code == 422


def test_failed_webhook_can_be_retried_only_by_owner(saas):
    client, engine, _ = saas
    owner, other = tenant(client, "Owner"), tenant(client, "Other")
    candidate = person(client, engine, owner)
    submit(client, new_session(client, owner, candidate["id"]))
    with Session(engine, expire_on_commit=False) as db:
        delivery = db.scalar(select(WebhookDelivery))
        delivery.attempts = 4
        db.commit()
        deliver_one(db, post=lambda *_a, **_k: SimpleNamespace(status_code=500))
        assert delivery.status == "failed"
        delivery_id = delivery.id
    assert client.post(f"/v1/webhooks/{delivery_id}/retry", headers=other["operator"]).status_code == 404
    assert client.post(f"/v1/webhooks/{delivery_id}/retry", headers=owner["operator"]).status_code == 200
