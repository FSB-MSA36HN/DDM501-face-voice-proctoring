# Product requirements - scope approved 29/09/2026

## Business and users

Doanh nghi?p t? ch?c k? ??nh gi? ngo?i ng? th??ng ni?n, c?n t?n hi?u ch?ng thi h?/gi? m?o m? v?n d?ng ph?n m?m thi hi?n t?i. Admin c?ng ty qu?n l? nh?n vi?n v? b?o c?o. Backend c?ng ty g?i batch face/voice theo l?ch ri?ng v? quy?t ??nh nghi?p v?. Platform team v?n h?nh model, web v? MLOps.

## Required product capabilities

- Simulated active company registration, tenant isolation, operator/integration keys and approved webhook configuration.
- Employee identifiers scoped to company; face/WAV enrollment via portal and API, consent supplied by customer, embeddings in PostgreSQL.
- POST /v1/checks: identity matching, capture-integrity details, stable codes/labels, request idempotency, immutable history and signed outbox callback.
- Face count, face PAD, synthetic/converted audio signal, exact capture reuse and speaker-change heuristic; unavailable/insufficient checks explicitly inconclusive.
- Suspicious-only MinIO image/audio evidence with scoped authenticated downloads; ordinary raw captures discarded.
- Employee/session first-last check ranges and history; PDF/CSV filters and export. No exam scores/admission decisions in primary portal.
- Existing hosted session/manual review APIs remain compatibility examples, outside required product flow.

## Required course MLOps

Snapshot/lineage -> validation -> calibration/CV/holdout -> MLflow Registry -> RAI -> promotion -> serving reload -> Grafana/Evidently -> platform Telegram. Docker, CI/CD, self-hosted demo deployment, backup/rollback evidence, rubric mapping, business report and presentation.

## Boundaries and acceptance

Cadence/batch capture belongs to customer. Registration is simulated, not paid billing or verified organization onboarding. API keys serve as course MVP access control; no production SSO. Identity gates remain demo FAR/FRR <=20%; coverage of declared first-party modules >=80%. No local anti-spoof accuracy gate is claimed without labelled benchmark. Two-company isolation must pass on people/checks/exports/evidence/keys. API success and callback must describe the same check. Telegram is for platform operations only. Data retained while simulated subscription active; disabled subscription denies tenant access without data deletion.

## Known development limits

CPU/local deployment, synthetic cross-dataset bootstrap identities, no validated demographic fairness or customer anti-spoof accuracy. Single-image PAD is not universal video deepfake detection. Segment consistency is not overlap diarization. Physical playback is not proven by ASVspoof-LA. Consent scope, real labels, onboarding verification, SSO/billing/deletion, temporal liveness and cloud scaling are future pilot work. Proposed business improvements are not measured customer outcomes.
