import importlib
import io

import cv2
import numpy as np
import pytest
from app.biometrics import BiometricEngine
from app.config import get_settings
from app.db import get_db
from app.models import WebhookDelivery
from app.registry import RuntimeModel
from fastapi.testclient import TestClient
from scipy.io import wavfile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


class MemoryEvidence:
    def __init__(self):
        self.objects = {}

    def put(self, *args):
        return None

    def put_evidence(self, tenant_id, event_id, modality, payload, content_type):
        key = f'{tenant_id}/{event_id}/{modality}'
        self.objects[key] = (payload, content_type)
        return key

    def get(self, key):
        return self.objects[key]


@pytest.fixture
def checks_api(monkeypatch, tmp_path):
    monkeypatch.setenv('API_KEY', 'checks-platform')
    monkeypatch.setenv('MODEL_BACKEND', 'demo')
    monkeypatch.setenv('STORE_RAW_BIOMETRICS', 'false')
    get_settings.cache_clear()
    main = importlib.import_module('app.main')
    engine = create_engine(f"sqlite:///{(tmp_path/'checks.db').as_posix()}", connect_args={'check_same_thread': False})
    monkeypatch.setattr(main, 'engine', engine)
    monkeypatch.setattr(main, 'settings', get_settings())
    monkeypatch.setattr(main, 'biometrics', BiometricEngine(get_settings()))
    monkeypatch.setattr(main.registry, 'current', RuntimeModel(.45, .25, 'check-test'))
    monkeypatch.setattr(main.registry, 'load', lambda: main.registry.current)
    store = MemoryEvidence()
    monkeypatch.setattr(main, 'object_store', store)
    monkeypatch.setattr(main.app.state, 'inspect_integrity', lambda *args: {
        'face_pad': {'status': 'passed'}, 'audio_spoof': {'status': 'passed'},
        'speaker_consistency': {'status': 'passed'},
    }, raising=False)

    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    main.app.dependency_overrides[get_db] = database
    image = np.zeros((160, 160, 3), dtype=np.uint8)
    image[::8, :] = 255
    image[:, ::8] = 255
    _, encoded = cv2.imencode('.png', image)
    stream = io.BytesIO()
    wavfile.write(stream, 16000, (np.sin(np.arange(160000)*2*np.pi*220/16000)*20000).astype(np.int16))
    media = {'face_file': ('face.png', encoded.tobytes(), 'image/png'),
             'voice_file': ('voice.wav', stream.getvalue(), 'audio/wav')}
    with TestClient(main.app) as client:
        yield client, engine, store, media, main
    main.app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def company(client, name):
    row = client.post('/v1/admin/tenants', headers={'X-API-Key': 'checks-platform'}, json={
        'name': name, 'webhook_url': 'http://legacy-demo:8000/webhooks/verification',
    }).json()
    for role in ('operator', 'integration'):
        row[role] = {'X-API-Key': client.post(f"/v1/admin/tenants/{row['id']}/keys",
                    headers={'X-API-Key': 'checks-platform'}, json={'role': role}).json()['api_key']}
    return row


def employee(client, owner, media):
    row = client.post('/v1/people', headers=owner['operator'], json={
        'external_id': 'EMP-001', 'display_name': 'Nguyễn Văn An',
    }).json()
    r = client.post(f"/v1/people/{row['id']}/enroll", headers=owner['operator'],
                    files=[('face_files', media['face_file']), ('voice_files', media['voice_file'])])
    assert r.status_code == 200, r.text
    return row


def send(client, owner, person, media, request_id='capture-1', session_id='ANNUAL-2026'):
    return client.post('/v1/checks', headers=owner['integration'], files=media,
                       data={'person_id': person['id'], 'session_id': session_id,
                             'request_id': request_id, 'consent': 'true'})


def test_batch_check_integration_idempotency_and_webhook(checks_api):
    client, engine, store, media, _ = checks_api
    owner = company(client, 'First company')
    person = employee(client, owner, media)
    r = send(client, owner, person, media)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result['integrity_status'] == 'verified'
    assert result['face_match'] and result['voice_match']
    assert result['employee_name'] == 'Nguyễn Văn An'
    assert send(client, owner, person, media).json()['check_id'] == result['check_id']
    assert send(client, owner, person, media, session_id='DIFFERENT').status_code == 409
    assert store.objects == {}
    with Session(engine) as db:
        rows = db.scalars(select(WebhookDelivery)).all()
        assert len(rows) == 1
        assert rows[0].payload['type'] == 'integrity.checked'
        assert rows[0].payload['data'] == result


def test_suspicious_only_evidence_and_full_tenant_isolation(checks_api, monkeypatch):
    client, _, store, media, main = checks_api
    first, second = company(client, 'First'), company(client, 'Second')
    p1, p2 = employee(client, first, media), employee(client, second, media)
    monkeypatch.setattr(main.app.state, 'inspect_integrity', lambda *args: {
        'face_pad': {'status': 'failed', 'score': .95},
        'audio_spoof': {'status': 'passed'}, 'speaker_consistency': {'status': 'passed'},
    })
    r = send(client, first, p1, media)
    assert r.status_code == 200, r.text
    result = r.json()
    assert result['integrity_status'] == 'suspicious'
    assert 'face_spoof_suspected' in result['reason_codes']
    assert result['evidence_status'] == 'stored' and len(store.objects) == 2
    assert all(k.startswith(first['id']+'/') for k in store.objects)
    check_id = result['check_id']
    assert client.get(f'/v1/checks/{check_id}', headers=second['operator']).status_code == 404
    assert send(client, second, p1, media).status_code == 404
    assert client.get('/v1/checks', headers=second['operator']).json()['items'] == []
    assert client.get(f'/v1/checks/{check_id}/evidence/face', headers=second['operator']).status_code == 404
    assert client.get(f'/v1/checks/{check_id}/evidence/face').status_code == 401
    image = client.get(f'/v1/checks/{check_id}/evidence/face', headers=first['operator'])
    assert image.content == media['face_file'][1] and image.headers['content-type'] == 'image/png'
    assert p1['external_id'] == p2['external_id']


def test_missing_detector_is_inconclusive_without_evidence(checks_api, monkeypatch):
    client, _, store, media, main = checks_api
    owner = company(client, 'Missing detector')
    p = employee(client, owner, media)
    monkeypatch.setattr(main.app.state, 'inspect_integrity', lambda *args: {
        'face_pad': {'status': 'unavailable'}, 'audio_spoof': {'status': 'passed'},
        'speaker_consistency': {'status': 'passed'},
    })
    r = send(client, owner, p, media)
    assert r.status_code == 200, r.text
    assert r.json()['integrity_status'] == 'inconclusive'
    assert store.objects == {}


def test_reports_include_ranges_unicode_and_isolate_filters(checks_api):
    client, _, _, media, _ = checks_api
    first, second = company(client, 'Report owner'), company(client, 'Other reports')
    p1 = employee(client, first, media)
    employee(client, second, media)
    assert send(client, first, p1, media).status_code == 200
    report = client.get('/v1/company/report', headers=first['operator']).json()
    assert report['employees'][0]['first_check_at'] and report['employees'][0]['last_check_at']
    assert report['employees'][0]['checks'] == 1
    assert client.get('/v1/company/report', headers=second['operator']).json()['checks'] == []
    assert client.get('/v1/company/report?person_id='+p1['id'], headers=second['operator']).status_code == 404
    csv = client.get('/v1/company/report.csv', headers=first['operator'])
    assert csv.status_code == 200 and 'Nguyễn Văn An' in csv.content.decode('utf-8-sig')
    pdf = client.get('/v1/company/report.pdf', headers=first['operator'])
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
    assert client.get('/v1/company/report.csv').status_code == 401


def test_registration_and_company_key_configuration(checks_api):
    client, _, _, _, _ = checks_api
    r = client.post('/v1/registrations', json={'name': 'Registered company'})
    assert r.status_code == 201, r.text
    headers = {'X-API-Key': r.json()['operator_key']}
    assert client.get('/v1/company', headers=headers).json()['name'] == 'Registered company'
    assert client.patch('/v1/company', headers=headers, json={'webhook_url': 'http://localhost:18600/webhooks/verification'}).status_code == 200
    assert client.patch('/v1/company', headers=headers, json={'webhook_url': 'http://169.254.169.254/'}).status_code == 422
    key = client.post('/v1/company/keys', headers=headers).json()
    assert client.get('/v1/me', headers={'X-API-Key': key['api_key']}).json()['role'] == 'integration'
    assert client.delete('/v1/company/keys/'+key['id'], headers=headers).status_code == 200
    assert client.get('/v1/me', headers={'X-API-Key': key['api_key']}).status_code == 401
