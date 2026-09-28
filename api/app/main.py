from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .biometrics import BiometricEngine, BiometricError, cosine
from .config import get_settings
from .db import engine, get_db
from .auth import Principal, authenticate, audit, digest, get_person, operator, platform
from .migrations import migrate
from .decision import decide
from .explainability import explain
from .metrics import FEEDBACK, LATENCY, MODEL_INFO, PEOPLE, REQUESTS, VERIFY
from .models import BiometricSample, Person, VerificationEvent, VerificationFeedback
from .registry import RegistryLoader
from .schemas import EnrollmentOut, FeedbackIn, PersonCreate, PersonOut, SimulationIn, VerificationOut
from .storage import ObjectStore, sha256

settings = get_settings()
biometrics = BiometricEngine(settings)
object_store = ObjectStore(settings)
registry = RegistryLoader(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate(engine)
    try:
        registry.load()
    except Exception as exc:
        logging.getLogger(__name__).warning("Champion unavailable at startup; type=%s", type(exc).__name__)
    MODEL_INFO.labels(version=registry.current.version, backend=settings.model_backend).set(1)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    route_name = getattr(route, "path", request.url.path)
    REQUESTS.labels(route=route_name, status=str(response.status_code)).inc()
    return response


require_key = authenticate


async def read_upload(upload: UploadFile, allowed: set[str]) -> bytes:
    if upload.content_type not in allowed:
        raise HTTPException(status_code=415, detail=f"Không hỗ trợ {upload.content_type}")
    payload = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(payload) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp quá lớn")
    if not payload:
        raise HTTPException(status_code=400, detail="Tệp rỗng")
    return payload


def person_out(person: Person) -> PersonOut:
    face_count = sum(sample.modality == "face" for sample in person.samples)
    voice_count = sum(sample.modality == "voice" for sample in person.samples)
    return PersonOut(
        id=person.id,
        external_id=person.external_ref or person.external_id,
        display_name=person.display_name,
        active=person.active,
        created_at=person.created_at,
        face_samples=face_count,
        voice_samples=voice_count,
        ready=face_count >= settings.min_face_samples and voice_count >= settings.min_voice_samples,
    )


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(select(1))
    return {
        "status": "healthy",
        "backend": settings.model_backend,
        "model_version": registry.current.version,
        "raw_storage": settings.store_raw_biometrics,
    }


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    result = health(db)
    if registry.current.version == "local-default":
        raise HTTPException(503, "No registered champion loaded yet")
    return result


@app.post("/v1/people", response_model=PersonOut, status_code=201, dependencies=[Depends(require_key)])
def create_person(body: PersonCreate, db: Session = Depends(get_db), principal: Principal = Depends(authenticate)) -> PersonOut:
    internal_id = body.external_id if principal.tenant_id == "demo" else digest(principal.tenant_id + ":" + body.external_id)
    person = Person(external_id=internal_id, external_ref=body.external_id,
                    display_name=body.display_name, tenant_id=principal.tenant_id)
    db.add(person)
    try:
        audit(db, principal, "person.created", body.external_id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="external_id đã tồn tại") from exc
    db.refresh(person)
    PEOPLE.set(db.scalar(select(func.count(Person.id))) or 0)
    return person_out(person)


@app.get("/v1/people", response_model=list[PersonOut], dependencies=[Depends(require_key)])
def list_people(db: Session = Depends(get_db), principal: Principal = Depends(authenticate)) -> list[PersonOut]:
    people = db.scalars(select(Person).where(Person.tenant_id == principal.tenant_id)
                        .order_by(Person.created_at.desc()).limit(500)).unique().all()
    return [person_out(person) for person in people]


@app.post("/v1/people/{person_id}/enroll", response_model=EnrollmentOut, dependencies=[Depends(require_key)])
async def enroll(
    person_id: str,
    face_files: list[UploadFile] | None = File(default=None),
    voice_files: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(operator),
) -> EnrollmentOut:
    person = get_person(db, person_id, principal)
    face_added = voice_added = 0
    rejected: list[str] = []
    for modality, files in (("face", face_files or []), ("voice", voice_files or [])):
        for upload in files:
            try:
                allowed = {"image/jpeg", "image/png", "image/webp"} if modality == "face" else {"audio/wav", "audio/x-wav", "audio/wave"}
                payload = await read_upload(upload, allowed)
                result = await run_in_threadpool(biometrics.face if modality == "face" else biometrics.voice, payload)
                digest = sha256(payload)
                duplicate = db.scalar(
                    select(BiometricSample.id).where(
                        BiometricSample.person_id == person_id,
                        BiometricSample.modality == modality,
                        BiometricSample.sha256 == digest,
                    )
                )
                if duplicate:
                    rejected.append(f"{upload.filename}: trùng mẫu")
                    continue
                extension = "jpg" if modality == "face" else "wav"
                key = object_store.put(person_id, modality, payload, extension)
                db.add(BiometricSample(person_id=person_id, modality=modality, embedding=result.embedding.tolist(), quality=result.quality, object_key=key, sha256=digest))
                if modality == "face":
                    face_added += 1
                else:
                    voice_added += 1
            except (BiometricError, HTTPException) as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                rejected.append(f"{upload.filename}: {detail}")
    if not face_files and not voice_files:
        raise HTTPException(status_code=400, detail="Cần ít nhất một tệp")
    audit(db, principal, "person.enrolled", person_id)
    db.commit()
    db.refresh(person)
    output = person_out(person)
    return EnrollmentOut(person_id=person_id, face_added=face_added, voice_added=voice_added, rejected=rejected, ready=output.ready)


async def perform_verification(
    person_id: str, session_id: str, face_file: UploadFile | None, voice_file: UploadFile | None,
    db: Session, principal: Principal,
) -> VerificationOut:
    started = time.perf_counter()
    person = get_person(db, person_id, principal)
    enrolled = {"face": [], "voice": []}
    for sample in person.samples:
        enrolled[sample.modality].append(sample.embedding)
    reasons: list[str] = []
    scores: dict[str, float | None] = {"face": None, "voice": None}
    qualities: dict[str, float | None] = {"face": None, "voice": None}
    incoming = {"face": face_file, "voice": voice_file}
    for modality, upload in incoming.items():
        if upload is None:
            if settings.require_both_modalities:
                reasons.append(f"missing_{modality}")
            continue
        if not enrolled[modality]:
            reasons.append(f"not_enrolled_{modality}")
            continue
        allowed = {"image/jpeg", "image/png", "image/webp"} if modality == "face" else {"audio/wav", "audio/x-wav", "audio/wave"}
        payload = await read_upload(upload, allowed)
        try:
            result = await run_in_threadpool(biometrics.face if modality == "face" else biometrics.voice, payload)
        except BiometricError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        scores[modality] = max(cosine(result.embedding, reference) for reference in enrolled[modality])
        qualities[modality] = result.quality
    thresholds = {"face": registry.current.face_threshold, "voice": registry.current.voice_threshold}
    policy_accepted, risk, policy_reasons = decide(scores, qualities, thresholds, settings.require_both_modalities)
    reasons.extend(policy_reasons)
    accepted = policy_accepted and not reasons
    latency_ms = round((time.perf_counter() - started) * 1000)
    event = VerificationEvent(
        person_id=person_id, session_id=session_id, accepted=accepted, risk_score=risk,
        face_score=scores["face"], voice_score=scores["voice"], face_quality=qualities["face"],
        voice_quality=qualities["voice"], reasons=reasons, model_version=registry.current.version, latency_ms=latency_ms,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    decision = "allow" if accepted else "review"
    VERIFY.labels(decision=decision).inc()
    LATENCY.observe(latency_ms / 1000)
    return VerificationOut(
        event_id=event.id, person_id=person_id, session_id=session_id, accepted=accepted, decision=decision,
        risk_score=round(risk, 4), face_score=scores["face"], voice_score=scores["voice"],
        face_quality=qualities["face"], voice_quality=qualities["voice"], thresholds=thresholds,
        reasons=reasons, model_version=registry.current.version, latency_ms=latency_ms,
        explanations=explain(scores, qualities, thresholds, settings.require_both_modalities),
    )


@app.post("/v1/verify", response_model=VerificationOut)
async def verify(
    person_id: str = Form(...), session_id: str = Form(...),
    face_file: UploadFile | None = File(default=None), voice_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db), principal: Principal = Depends(operator),
) -> VerificationOut:
    result = await perform_verification(person_id, session_id, face_file, voice_file, db, principal)
    audit(db, principal, "verification.direct", result.event_id)
    db.commit()
    return result


@app.get("/v1/events", dependencies=[Depends(require_key)])
def events(limit: int = 100, db: Session = Depends(get_db), principal: Principal = Depends(authenticate)) -> list[dict]:
    rows = db.scalars(select(VerificationEvent).join(Person).where(Person.tenant_id == principal.tenant_id)
                      .order_by(VerificationEvent.created_at.desc()).limit(max(1, min(limit, 500)))).all()
    return [
        {"id": row.id, "person_id": row.person_id, "session_id": row.session_id, "accepted": row.accepted,
         "risk_score": row.risk_score, "face_score": row.face_score, "voice_score": row.voice_score,
         "reasons": row.reasons, "model_version": row.model_version, "latency_ms": row.latency_ms,
         "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@app.post("/v1/simulation/observations", response_model=VerificationOut, dependencies=[Depends(require_key)])
def simulate_observation(body: SimulationIn, db: Session = Depends(get_db), principal: Principal = Depends(platform)) -> VerificationOut:
    """Inject score observations for drift demos; disabled unless explicitly configured."""
    if not settings.enable_simulation:
        raise HTTPException(status_code=404, detail="Simulation endpoint is disabled")
    get_person(db, body.person_id, principal)
    scores = {"face": body.face_score, "voice": body.voice_score}
    qualities = {"face": body.face_quality, "voice": body.voice_quality}
    thresholds = {"face": registry.current.face_threshold, "voice": registry.current.voice_threshold}
    accepted, risk, reasons = decide(scores, qualities, thresholds, settings.require_both_modalities)
    event = VerificationEvent(
        person_id=body.person_id, session_id=body.session_id, accepted=accepted, risk_score=risk,
        face_score=body.face_score, voice_score=body.voice_score, face_quality=body.face_quality,
        voice_quality=body.voice_quality, reasons=reasons, model_version=registry.current.version,
        latency_ms=0,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    decision = "allow" if accepted else "review"
    VERIFY.labels(decision=decision).inc()
    return VerificationOut(
        event_id=event.id, person_id=body.person_id, session_id=body.session_id,
        accepted=accepted, decision=decision, risk_score=round(risk, 4),
        face_score=body.face_score, voice_score=body.voice_score,
        face_quality=body.face_quality, voice_quality=body.voice_quality,
        thresholds=thresholds, reasons=reasons, model_version=registry.current.version, latency_ms=0,
        explanations=explain(scores, qualities, thresholds, settings.require_both_modalities),
    )


@app.put("/v1/events/{event_id}/feedback", status_code=201, dependencies=[Depends(require_key)])
def add_feedback(event_id: str, body: FeedbackIn, db: Session = Depends(get_db), principal: Principal = Depends(operator)) -> dict:
    if db.scalar(select(VerificationEvent).join(Person).where(
        VerificationEvent.id == event_id, Person.tenant_id == principal.tenant_id,
    )) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy event")
    existing = db.scalar(select(VerificationFeedback).where(VerificationFeedback.event_id == event_id))
    if existing:
        existing.is_genuine, existing.reviewer, existing.notes = body.is_genuine, body.reviewer, body.notes
        feedback = existing
    else:
        feedback = VerificationFeedback(event_id=event_id, **body.model_dump())
        db.add(feedback)
    audit(db, principal, "feedback.updated", event_id)
    db.commit()
    db.refresh(feedback)
    FEEDBACK.labels(label="genuine" if body.is_genuine else "impostor").inc()
    return {"event_id": event_id, "is_genuine": feedback.is_genuine, "reviewer": feedback.reviewer}


@app.post("/v1/admin/reload-model", dependencies=[Depends(platform)])
def reload_model() -> dict:
    try:
        runtime = registry.load()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Không tải được model Registry") from exc
    MODEL_INFO.clear()
    MODEL_INFO.labels(version=runtime.version, backend=settings.model_backend).set(1)
    return runtime.__dict__


from .saas import router as saas_router  # noqa: E402
app.state.perform_verification = perform_verification
app.include_router(saas_router)


@app.exception_handler(Exception)
async def unhandled_exception(_, exc: Exception):
    REQUESTS.labels(route="unhandled", status="500").inc()
    return JSONResponse(status_code=500, content={"detail": "Lỗi nội bộ", "type": type(exc).__name__})
