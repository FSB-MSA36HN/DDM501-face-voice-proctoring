# Hai mapping theo yêu cầu DDM501

Đối chiếu `ddm501-final-project-required/DDM501_Final_Project.docx.pdf` và `MLOps_full_pipeline.txt`. Đây là mapping bằng chứng, không tự gán điểm thay giảng viên. Kết quả chạy mới nhất nằm ở [VERIFICATION.md](VERIFICATION.md).

## 1. Mapping tiêu chí chấm điểm

| Tiêu chí | Trọng số | Phần đã thực hiện | Phần còn cần bằng chứng/tham gia |
|---|---:|---|---|
| Problem / requirements | 10% | B2B SaaS use cases, prioritized requirements, business/model/system targets; capacity/cost worksheet | Business targets phải đo trên pilot thật |
| Architecture | 15% | Serving/control plane, tenant isolation, session binding, HMAC outbox, worker, private overlay; diagrams/trade-offs | Cloud/customer architecture cần host/domain thật |
| ML pipeline | 15% | Fingerprinted snapshot, tenant scope, validation, frozen pretrained features, 1.151 threshold trials, three objectives, identity CV + untouched holdout, MLflow nested runs/lineage/signature, gates | Consented real identity dataset và benchmark ngoài bootstrap |
| Deployment | 15% | FastAPI/OpenAPI, Docker/health/readiness, hosted verify/portal/legacy, packaged weights, runner preserves DB/assets, backup/restore và rollback drill | Local PaaS simulation không chứng minh public cloud/TLS/SSO; camera/mic cần browser acceptance |
| Monitoring | 10% | Grafana tập trung quality/drift/Registry/performance/review/DAG/RAI/resources/logs; protected reports; Prometheus → Alertmanager → Telegram verified | Human accuracy/fairness chờ nhãn thật; không dùng synthetic thay thế |
| Testing / CI/CD | 15% | Unit/API/media-upload/data/model/SaaS/collector/transport tests; coverage toàn API/monitoring + selected evaluation modules ≥80%; GitHub quality/build/deploy workflow và runner Windows | Chỉ tính remote CI/deploy khi có run thành công đúng source; xem VERIFICATION.md |
| Responsible AI | 10% | Consent, source-separated labels, immutable prediction/manual appeal, quality slices, Wilson 95% CI; reason codes/margins/sensitivity/counterfactual; RAI trước promotion | Human gate hiện insufficient_data; chưa demographic fairness/PAD/audio anti-spoof |
| Documentation | 10% | README/badge, API examples, architecture/integration/operations/deployment, hai mappings, capacity/cost, 12-slide PowerPoint có notes | Nhóm rà soát và điền tên/contribution thật |

### Presentation và contribution

Rubric thuyết trình riêng: introduction 15%, content 40%, demo 15%, Q&A 15%, organization 15%. [Slide](docs/DDM501_Face_Voice_Proctoring.pptx) và [kịch bản](DEMO_PRESENTATION.md) bao phủ các phần này. Mỗi thành viên phải trình bày/Q&A thật; contribution có thể điều chỉnh ±20%. Không tạo tên, nhãn human, commit hay phân công giả. Quyền truy cập giảng viên chưa được xác minh.

## 2. Mapping full pipeline

| Bước yêu cầu | Code / công cụ | Bằng chứng / giới hạn |
|---|---|---|
| Ingest/enrollment | API enroll, bootstrap/provision scripts | Consent/session audit, uploaded media, sample dedup; bootstrap face/voice ghép tổng hợp |
| Version data | `data_snapshot.py`, `snapshot_stats.py` | Snapshot per DAG run, SHA-256, default tenant demo |
| Clean/validate | `validate_data.py` | Reject invalid/zero vectors, inconsistent dimensions, duplicates, insufficient data |
| Feature engineering | `api/app/biometrics.py` | Decode/quality/resample/normalize; SFace/ECAPA frozen encoders |
| Train/tune | `calibrate_and_register.py`, `evaluation.py` | Threshold calibration/grid objectives; không claim fine-tune encoders |
| Experiment tracking | MLflow | Params/metrics/artifacts/signature + six nested objective runs |
| Evaluate | Identity-disjoint max-template CV + holdout | Serving-compatible scoring, holdout excluded from threshold tune; demo FAR/FRR gate ≤20% |
| Responsible AI | `responsible_ai_report.py` | Source/class counts, intervals, quality-gap status; audit precedes promotion |
| Registry/version | MLflow candidate/champion | Version-pinned artifacts, dataset fingerprint match, guarded CLI/DAG promotion |
| ML API | FastAPI `/v1/verify`, public sessions | Versioned REST/OpenAPI, validated upload, faithful explanation response |
| Serving/deploy | Compose + GitHub Windows runner | Readiness requires loaded champion; persistence paths preserved across checkout |
| Production observations | Verification events + feedback | Prediction immutable; human/synthetic reviewed subsets separate |
| Simulation/PSI | `simulate_drift.py`, drift-monitor | Explicit technical scenario, real PSI and Evidently HTML/JSON |
| Monitoring | Grafana/Prometheus/PostgreSQL/Loki | Seven dashboard sections; central authenticated reports; complete query checks |
| Alerting | Prometheus/Alertmanager/ops-monitor/Telegram | Firing/resolved forwarding, failure retry, real test delivery |
| Operation/recovery | Outbox/audit, recovery scripts, docs | Isolated restore row counts; champion rollback/readiness then restore original |
| Automation/CI/CD | `.github/workflows/ci.yml`, runner | Quality → container build → trusted-main deployment → Grafana verification artifact |

Theo file pipeline môn học, hai nửa training/Registry/API và serving/monitoring/operation đều có triển khai. DDM501 nhấn mạnh nửa serving → monitoring → operation. Không thiếu bước kỹ thuật trong mapping; các bằng chứng human/customer/cloud/team còn mở phải trình bày đúng phạm vi.

## Grafana và Telegram

[MONITORING_MAPPING.md](MONITORING_MAPPING.md) chỉ rõ từng phần monitoring nằm ở đâu trên Grafana. Bot `@ddm501_face_voice_proctoring_bot`; token/chat ID chỉ nằm trong `.env`. Grafana là trang quan sát chính; Airflow/MLflow giữ chức năng quản trị riêng. [OPERATIONS.md](OPERATIONS.md) có lệnh kiểm chứng và vận hành.
