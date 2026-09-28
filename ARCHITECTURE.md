# System architecture

```mermaid
flowchart LR
  UI[Streamlit] -->|REST + API key| API[FastAPI serving]
  API --> EMB[YuNet/SFace + ECAPA]
  API --> PG[(PostgreSQL events/features/feedback)]
  API -. optional raw .-> S3[(MinIO)]
  AF[Airflow] --> SNAP[versioned snapshot]
  SNAP --> DQ[data quality gate] --> TRAIN[feature pairs + threshold calibration]
  TRAIN --> MF[MLflow candidate + evaluation]
  MF --> RAI[RAI audit] --> EVAL[FAR/FRR + fingerprint promotion gate]
  EVAL -->|promote| MF
  MF -->|champion alias| API
  API --> PROM[Prometheus]
  PG --> DM[PSI + Evidently monitor]
  DM --> PROM --> GF[Grafana]
  PROM --> AM[Alertmanager]
  AM --> OPS[ops-monitor] --> TG[Telegram]
  MF --> OPS
  AF --> OPS
  PG --> OPS --> PROM
  Docker[Read-only Docker proxy] --> OPS
  Docker --> Alloy --> Loki --> GF
  PG --> GF
```

## Responsibilities and flows

The product boundary is a B2B SaaS API plus hosted verification and operator portal. Local Compose emulates separate PaaS services; a customer can run the same installation privately. `TenantKey` stores only hashed random credentials. All customer reads/writes scope people/events/sessions/audit to the authenticated tenant. Platform keys manage tenants and ML operations; integration keys cannot enroll biometrics, alter review labels or bypass the hosted session.

Session creation binds tenant, person, exam, request ID and expiry. The browser carries only a one-session bearer token in a URL fragment, never a tenant API key. An atomic conditional update prevents reuse. Inference event, completed session and webhook outbox commit in one DB transaction. A worker claims pending deliveries with PostgreSQL row locks, signs raw JSON with timestamp/HMAC and retries independently. Delivery can be duplicated after worker crashes; the customer receiver must deduplicate and fetch canonical API state. Manual review increments sequence without rewriting model predictions.

The legacy example runs on its own port/process/database and grants exam admission only after checking the server-side session/person/exam/tenant binding and expiry. Cookie state survives return navigation; an exam attempt is consumed once. Its candidate selector is a mock login, not a deployable authentication system.

The serving plane validates media, extracts normalized embeddings, compares them with the declared identity, applies the versioned policy, records an immutable event and returns modality scores/reason codes. A separate feedback table holds proctor labels so inference history is not rewritten.

The training plane freezes exact feature rows in a fingerprinted snapshot per DAG run. Validation and calibration consume that same snapshot; retries reuse it. MLflow stores the fingerprint, snapshot, validation, thresholds and identity evaluation artifacts. Max-template scoring matches serving. Five identity partitions reserve one holdout outside all training/tuning; the remaining four form internal CV. Threshold selection minimizes worst FAR/FRR, then their average; a fixed candidate set chooses the smallest conservative margin meeting the internal CV budget. Holdout is used only for final evaluation. Promotion requires calibration, CV and holdout FAR/FRR <=20%, valid class counts and matching fingerprint after RAI audit. API startup loads the champion by pinned version; hot reload keeps the old runtime on failure. Identity-disjoint demo evaluation still does not prove accuracy on consented real users.

The monitoring plane compares the preceding and current production windows, calculates PSI independently, generates an Evidently report, exports ML and system metrics, visualizes them in Grafana and routes threshold breaches to Alertmanager. `pipeline/simulate_drift.py` exercises the API rather than writing directly to the database.

With `--with-feedback`, simulation creates explicit synthetic labels under reviewer `synthetic-simulation` to exercise performance degradation. Evidently compares two non-overlapping labelled windows and exports accuracy/precision/recall/F1/FAR/FRR separately for human and synthetic sources. Insufficient human labels produce waiting status and NaN metrics. Grafana combines Prometheus, PostgreSQL and Loki, with authenticated HTML/JSON reports at the same origin. ops-monitor collects Registry, Airflow, RAI, readiness and Docker resources; Alertmanager notifications are forwarded to Telegram with retries on transport failure.

## Technology choices and trade-offs

| Choice | Why | Trade-off |
|---|---|---|
| FastAPI | typed OpenAPI, async uploads, simple validation | synchronous CPU inference limits throughput |
| PostgreSQL JSON embeddings | transparent demo/audit and simple joins | pgvector/object features needed at scale |
| MLflow + MinIO | portable experiment/artifact/alias lifecycle | more services and credentials |
| Airflow LocalExecutor | visible retries/scheduling and course alignment | too heavy for a single small job; not horizontally scalable |
| Prometheus/Grafana/Evidently | system + ML monitoring with inspectable reports | Evidently batch report is not real-time stream processing |
| pretrained embeddings + calibrated policy | avoids pretending to train foundation models on tiny data | calibration quality depends on representative consented data |

## Failure and edge cases

Invalid media returns 4xx; missing weights fail closed; duplicate enrollment is rejected; insufficient training pairs fail the DAG; failed model gates preserve the current champion; Registry reload failure returns 503 without dropping the loaded version; insufficient drift samples marks the monitor cycle failed/stale; raw media storage defaults off.
