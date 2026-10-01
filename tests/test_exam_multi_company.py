import importlib
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient


def test_exam_selects_tenant_server_side_and_rejects_cross_tenant(monkeypatch, tmp_path):
    demo = importlib.import_module('legacy_demo.app')
    primary = {'tenant_id': 'a', 'integration_key': 'key-a', 'webhook_secret': 'secret-a'}
    (tmp_path / 'local-saas.json').write_text(json.dumps(primary))
    (tmp_path / 'company-demo.json').write_text(json.dumps({'companies': [
        {'tenant_id': 'b', 'name': 'Company B', 'integration_key': 'key-b', 'webhook_secret': 'secret-b'}]}))
    monkeypatch.setattr(demo, 'CONFIG', tmp_path / 'local-saas.json')
    monkeypatch.setattr(demo, 'DATABASE', str(tmp_path / 'legacy.db'))
    calls = []

    def upstream(method, url, headers, **kwargs):
        calls.append((method, url, headers['X-API-Key']))
        if url.endswith('/v1/people'):
            key = headers['X-API-Key']
            return SimpleNamespace(ok=True, json=lambda: [{'id': 'person-' + key[-1],
                'display_name': 'Employee ' + key[-1], 'external_id': 'EMP-' + key[-1], 'ready': True}])
        return SimpleNamespace(ok=True, json=lambda: {'integrity_status': 'verified'})

    monkeypatch.setattr(demo.requests, 'request', upstream)
    with TestClient(demo.app) as browser:
        browser.get('/')
        companies = browser.get('/companies').json()
        assert [(item['id'], item['name']) for item in companies] == [('a', 'Demo nội bộ'), ('b', 'Company B')]
        assert browser.get('/candidates?company_id=b').json()[0]['id'] == 'person-b'
        media = {'face_file': ('face.jpg', b'face', 'image/jpeg'),
                 'voice_file': ('voice.wav', b'voice', 'audio/wav')}
        data = {'company_id': 'a', 'person_id': 'person-b', 'session_id': 'exam',
                'request_id': 'request-1', 'consent': 'true'}
        assert browser.post('/check', data=data, files=media).status_code == 404
        assert not any(url.endswith('/v1/checks') for _, url, _ in calls)
        data['company_id'] = 'b'
        assert browser.post('/check', data=data, files=media).json()['integrity_status'] == 'verified'
        assert calls[-1][2] == 'key-b'
