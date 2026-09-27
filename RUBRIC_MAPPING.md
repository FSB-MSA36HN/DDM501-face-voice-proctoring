# DDM501 rubric evidence

| Rubric | Evidence |
|---|---|
| Problem, requirements, success metrics | `PROJECT_REQUIREMENTS.md` |
| Architecture, data flow, decisions/trade-offs | `ARCHITECTURE.md` |
| Data ingestion/preprocessing/feature/training/evaluation | Airflow DAG and `pipeline/` quality, calibration and promotion scripts |
| Experiment tracking/registry | MLflow params, metrics, tags, artifact, signature and aliases in `calibrate_and_register.py` |
| REST deployment and orchestration | versioned FastAPI, OpenAPI, Dockerfiles and Compose health checks |
| Monitoring/dashboard/alerting | Prometheus rules, Grafana dashboard, Alertmanager, PSI exporter and Evidently HTML |
| Unit/integration/data/model tests | `tests/`; GitHub Actions enforces >80% core coverage and builds containers |
| Responsible AI | feedback endpoint, reason codes, `responsible_ai_report.py`, `RESPONSIBLE_AI.md` |
| Documentation | README, architecture, requirements, responsible AI, contributing and generated `/docs` OpenAPI |

## SaaS completion and evidence status (2026-09-27)

Đối chiếu cả PDF `DDM501_Final_Project.docx.pdf` và `MLOps_full_pipeline.txt`. Bảng này ghi phạm vi thực hiện, không tự chấm điểm/thay xác nhận của giảng viên.

| Nhóm tiêu chí | Bổ sung theo hướng SaaS | Bằng chứng / giới hạn |
|---|---|---|
| Requirements 10% | Khách hàng B2B, hosted verify, legacy integration, private deployment | PROJECT_REQUIREMENTS.md, SAAS_INTEGRATION.md |
| Architecture 15% | Tenant-scoped auth, expiring sessions, transactional outbox, independent worker | ARCHITECTURE.md, sơ đồ sequence trong SAAS_INTEGRATION.md |
| ML pipeline 15% | Snapshot cố định, scope training tenant, validation, grid search, calibration và pair CV | Airflow `saas_tenant_scope_20260927` success; MLflow version/metrics/artifacts; chưa identity-disjoint benchmark |
| Deployment 15% | API versioned, portal, hosted page, legacy app, PaaS image chứa weights và private overlay | Docker chạy local; PaaS được giả lập local, chưa public-cloud deployment |
| Monitoring 10% | PSI, Evidently drift/classification, webhook outcomes/backlog, meaningful alerts | Grafana, Prometheus targets/rules, Alertmanager; reports/verification.json |
| Testing & CI/CD 15% | Unit/API/data/model + tenant isolation/session replay/webhook tests; core coverage >80%; build/deploy workflow | tests/, pipeline/ci_local.ps1, reports/saas-verification.json; remote GitHub runner run cần cấu hình tài khoản |
| Responsible AI 10% | Consent phiên, operator review riêng model prediction, proxy fairness, đúng denominator FAR/FRR, tách synthetic/human | RESPONSIBLE_AI.md và data/reports/responsible-ai.json; chưa có dữ liệu demographic và đủ human feedback để kết luận fairness |
| Documentation 10% | Hợp đồng API/webhook, onboarding, deploy/backup/rollback, handoff | README, OPERATIONS, DEPLOYMENT, SAAS_INTEGRATION, PROJECT_STATE |
| Presentation/team | Kịch bản 15–20 phút và Q&A, phân công mẫu | DEMO_PRESENTATION.md, CONTRIBUTING.md; nhóm phải tự điền tên thật, làm meaningful commits và slide |

## Những gì không được gọi là đã hoàn thành thực tế

Remote GitHub Actions/deploy chưa có run xác nhận; quyền giảng viên và commit của từng thành viên chưa được xác minh; chưa public cloud/TLS deployment; không có chứng nhận production accuracy, demographic fairness hoặc chống giả mạo sinh trắc học. Các phần này phải trình bày trung thực, không suy ra từ demo synthetic.
