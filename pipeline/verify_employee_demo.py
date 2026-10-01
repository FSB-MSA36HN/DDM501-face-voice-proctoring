"""Live employee self-enrollment across two configured demo companies; no secret output."""
import json
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
API = 'http://localhost:18100'


def main():
    companies = json.loads((ROOT / 'data/company-demo.json').read_text(encoding='utf-8'))['companies']
    assert len(companies) >= 2
    session = requests.Session()
    session.trust_env = False
    evidence = []

    def call(method, path, expected=200, key=None, **kwargs):
        response = session.request(method, API + path, headers={'X-API-Key': key} if key else {},
                                   timeout=180, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f'{method} {path}: HTTP {response.status_code}, expected {expected}')
        return response

    for index, company in enumerate(companies[:2]):
        owner = company['operator_key']
        code = 'SELF-' + uuid.uuid4().hex[:8]
        person = call('POST', '/v1/people', 201, owner,
                      json={'external_id': code, 'display_name': f'Nhân viên tự ghi danh {index + 1}'}).json()
        invitation = call('POST', f"/v1/people/{person['id']}/enrollment-invitations", 201, owner).json()
        token = invitation['token']
        info = call('POST', '/v1/public/enrollment-invitations/inspect', data={'token': token}).json()
        assert info['display_name'] == person['display_name']
        folder = ROOT / 'data/bootstrap/DEMO-001'
        faces = sorted(folder.glob('face-*.jpg'))[:2]
        voices = sorted(folder.glob('voice-*.wav'))[:2]
        assert len(faces) == len(voices) == 2
        files = [('face_files', (p.name, p.read_bytes(), 'image/jpeg')) for p in faces]
        files += [('voice_files', (p.name, p.read_bytes(), 'audio/wav')) for p in voices]
        enrollment = call('POST', '/v1/public/enroll', data={'token': token, 'consent': 'true'},
                          files=files).json()
        assert enrollment['ready'] and enrollment['face_added'] == enrollment['voice_added'] == 2
        call('POST', '/v1/public/enroll', 404, data={'token': token, 'consent': 'true'}, files=files)
        people = call('GET', '/v1/people', key=owner).json()
        assert next(p for p in people if p['id'] == person['id'])['ready']
        evidence.append({'company': company['name'], 'employee': code, 'ready': True,
                         'single_submission': True, 'replay_rejected': True})

    first, second = companies[:2]
    call('POST', f"/v1/people/{person['id']}/enrollment-invitations", 404, first['operator_key'])
    output = {'status': 'pass', 'scenarios': evidence, 'tenant_isolation': 'pass',
              'note': 'Bootstrap media exercises transport and enrollment; it is not a human biometric accuracy benchmark.'}
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/employee-demo-verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
