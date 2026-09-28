# Problem definition and requirements

## Problem and business context

Remote English examinations need a low-friction way to check that the enrolled candidate remains the person taking the exam. Manual review of every session is costly; automatic rejection from imperfect biometrics is harmful. This system performs declared-identity face + voice verification and routes uncertain or failed checks to a human review queue. It is an integrity signal, not proof of cheating.

## Users and use cases

- Customer software vendor: integrate hosted verification using REST sessions and signed webhook callbacks without replacing the existing exam system.
- Tenant operator: manage only their organization's enrollment, sessions, reviews, feedback and outbox retries.
- Platform administrator: onboard tenants, issue/revoke scoped credentials, operate ML pipeline/monitoring; supply a private deployment package when requested.

- Candidate: enroll multiple consented face/WAV samples and submit a fresh verification.
- Proctor: inspect the decision, modality scores, quality, reason codes and model version; add ground-truth feedback.
- ML engineer: reproduce data validation/calibration, compare MLflow runs and promote only a gated candidate.
- Operator: inspect SLOs, PSI/Evidently drift, receive alerts and roll back by moving the MLflow `champion` alias.

## Prioritized requirements

| Priority | Requirement |
|---|---|
| Must | Versioned REST API, authentication, validation, explainable `ALLOW`/`REVIEW`, immutable event audit |
| Must | Airflow pipeline from snapshot and data quality through calibration, evaluation, Registry and deployment |
| Must | MLflow params/metrics/artifacts/signature and `candidate`/`champion` aliases |
| Must | Prometheus, Grafana, Alertmanager, Evidently report, PSI simulation and human-feedback performance |
| Must | Docker Compose health checks, tests and GitHub Actions |
| Must | Tenant isolation, expiring single-use sessions, consent, backend-bound results, signed durable webhook delivery |
| Must | Local legacy-system integration demo and admin/operator portal |
| Should | Portable serving image with pinned weights; documented private/on-premise overlay |
| Should | Raw biometric storage off by default, pinned datasets/models, review feedback and quality-slice audit |
| Could | Face PAD, audio anti-spoof, ASR phrase challenge, GPU autoscaling and canary routing |

## Target metrics

| Level | Metric | Target / gate |
|---|---|---|
| Business | automatically allowed genuine sessions | proposed pilot ≥70%, with no increase in the agreed false-accept bound; measure against consented baseline |
| Business | manual review effort per 1,000 sessions | proposed pilot ≥50% reduction; measure operator minutes before/after |
| Business | reviewed-event turnaround | < 15 minutes during exams |
| Model | FAR and FRR per modality | each <= 20% demo promotion gate; stricter threshold set from pilot risk policy |
| Model | quality-slice accuracy gap | <= 10 percentage points with >=20 human-reviewed cases and >=5 of each class per comparable slice |
| Data | invalid/duplicate/inconsistent embeddings | 0 entering training |
| Drift | PSI per production feature | investigate >=0.1; alert >0.2 for 2 minutes |
| System | availability | >=99.5% pilot target |
| System | p95 verification latency | <=2 seconds excluding first model warm-up |
| Engineering | declared API/monitoring/evaluation coverage | >=80%; whole `app`, whole `monitoring`, snapshot/evaluation/validation/promotion/RAI modules |
| Integration | accepted duplicate session submissions / cross-tenant accesses | 0 in integration tests |
| Integration | webhook delivery | at-least-once with retry; receiver deduplicates, 5 attempts before operator intervention |

## Constraints and non-goals

CPU-first local demo, 50–100 synthetic cross-dataset identities, no demographic ground truth and no claim of production biometric accuracy. `REVIEW` always requires a person. PAD/deepfake detection, high-concurrency scaling and regulatory certification are explicitly outside the MVP.

Capacity equations, assumptions and a cost worksheet are in [SCALABILITY_COST.md](SCALABILITY_COST.md). Business targets are proposed requirements, not achieved customer outcomes.
