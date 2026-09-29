# Kiểm chứng MLOps và company service (Asia/Saigon)

## Maintenance 29/09/2026

| Hạng mục | Bằng chứng mới |
|---|---|
| Quality | **65 tests pass, coverage 86,50%**; Ruff, compile, generated-dashboard diff và Compose config pass |
| Company batch | Hai tenant đăng ký, cùng mã nhân viên, SFace/ECAPA + MiniFASNet/AASIST thật; same identity verified, other identity suspicious |
| API consistency | Retry cùng request/payload trả cùng check; thay payload 409; kết quả/check/event/outbox cùng transaction |
| Isolation/storage | Check/evidence/export khác tenant 404; thiếu key 401; suspicious image/WAV lưu MinIO; ordinary check không giữ raw |
| Business reports | JSON/PDF/CSV theo nhân viên/phiên/ngày; first/last check ranges, labels và evidence status; không có điểm thi |
| Callbacks | Signed customer webhooks delivered, receiver HTTP 200; verifier poll kiểm tra ACK cho từng check |
| Multi-capture | Ảnh ghép hai mặt và audio ghép hai người có `multiple_faces`, `multiple_speakers_suspected`; chỉ là scenario inference |
| Portal | Streamlit AppTest chạy sáu trang của cả hai tenant, đăng ký anonymous và inline CSV export với API thật |
| Monitoring | 62 panels, 67 queries; dashboard queries, freshness, protected reports/sources pass; short/multi-face capture không bị coi là detector outage |
| GitHub CI/CD | [Run 36562882154](https://github.com/TrinhDucDuong/ddm501-face-voice-proctoring/actions/runs/36562882154) success: quality, containers, deploy-demo; remote 65 tests, coverage 86,45% |
| Deployed code | Release `8b720fc1a30ba16754c785020325e40de27c02e4` ngoài OneDrive; company/callback/isolation/evidence/export và monitoring kiểm tra lại sau deploy pass |

Artifacts mới: `reports/company-verification.json`, `multiple-capture-verification.json`, `company-demo.pdf/csv`, `ui-verification.log`, `coverage-maintenance.json`, `tests-maintenance.xml`, `monitoring-verification.json`. Không đưa credentials/media/runtime artifacts lên GitHub. Camera/mic, browser playback/download và anti-spoof customer benchmark chưa được xác thực bằng những checks này.

## Baseline full pipeline 28/09/2026

Bằng chứng runtime tại `reports/verification.json`, `monitoring-verification.json`, `coverage.json`, `saas-verification.json`, `paas-verification.json`, `recovery-verification.json`, `github-actions.json`. Các file này/data/models/backups chứa dữ liệu runtime, được gitignore. Tài liệu ghi kết quả thực chạy; không thay thế điểm do giảng viên chấm.

## Pipeline, serving và chất lượng

| Hạng mục | Kết quả thực tế |
|---|---|
| Airflow | Run `isolated_holdout_20260928`: 6/6 tasks success, RAI trước promotion và reload API |
| Snapshot/validation | 282 feature rows, training tenant demo; snapshot SHA-256 cố định theo run, validation trước calibration |
| MLflow | Champion **9**, run `4068c96a6c13401bae5f91ab250cfdcb`; params/metrics/snapshot/validation/evaluation/signature và nested objective runs |
| Evaluation | Identity-disjoint max-template cosine giống serving; năm partitions, holdout riêng + bốn folds CV nội bộ; margin chọn bằng CV, không dùng holdout |
| Gates | Calibration/CV/holdout FAR và FRR ≤20%, holdout sample counts và dataset fingerprint; reject invalid/NaN metrics, CLI không bypass |
| API | Backend `pretrained`, loaded champion 9, readiness pass; giữ model trước nếu reload thất bại |
| Ảnh/WAV thật | Cùng danh tính ALLOW, score 1/1; khác danh tính REVIEW, face 0,19485 và voice 0,10871; reasons/margins/sensitivity/counterfactual theo policy |
| Tests | **52 passed**, coverage **88,76%**, Ruff/diff checks pass |
| Phạm vi coverage | Toàn `app`, toàn `monitoring`, `pipeline.evaluation`, `data_snapshot`, `validate_data`, `promotion_gate`, `responsible_ai_report`; không phải toàn repository |
| Live SaaS | **19 checks pass**: tenant isolation, consent, expiry/one-time session, genuine/impostor upload, operator review, HMAC callbacks, single exam admission |

### FAR/FRR của champion 9

| Modality | Threshold | Calibration FAR / FRR | Internal CV FAR / FRR | Reserved holdout FAR / FRR | Holdout genuine / impostor |
|---|---:|---:|---:|---:|---:|
| Face | 0,374 | 0% / 0% | 0,56% / 0% | 0% / 0% | 27 / 55 |
| Voice | 0,221 | 14,73% / 16,39% | 19,60% / 16,47% | 18,18% / 16,67% | 30 / 55 |

Margin ứng viên cố định: 0; 0,002; 0,005; 0,01; 0,02. Chọn margin nhỏ nhất đạt gate bằng internal CV; face 0, voice 0,002. Holdout không nằm trong train/test của bất kỳ inner fold nào. Regression test thay riêng embeddings holdout chứng minh threshold/CV không đổi. Nếu không có margin đạt, giữ kết quả fail để promotion từ chối.

## Grafana và Telegram

| Hạng mục | Kết quả |
|---|---|
| Dashboard | **59 panels gồm 7 row headers**, **64 truy vấn** PromQL/SQL/LogQL đã thực thi không lỗi |
| Monitoring coverage | Readiness/latency/errors, training quality, PSI/Evidently, human/synthetic classification, Registry/calibration/CV/holdout, sessions/review SLA, webhooks, DAG/tasks, RAI, CPU/RAM/network/IO, logs |
| Metrics/collectors | API/drift/webhook/ops scrape UP; DB/Registry/Airflow/Docker collectors thành công và freshness hợp lệ |
| Logs/resources | Alloy v1.20.0 → Loki; Docker stats qua read-only socket proxy; theo Compose project |
| Reports | Tám report HTML/JSON cùng origin Grafana; anonymous 401, authenticated 200 |
| Human evidence | Report `waiting_for_feedback`, fairness `insufficient_data`; synthetic là nguồn/report/alert riêng |
| Alert delivery | Alertmanager → ops-monitor → **Telegram đã gửi thành công**, cả kiểm thử trực tiếp và webhook; bot `@ddm501_face_voice_proctoring_bot` |

Truy vấn không lỗi không đồng nghĩa mọi series có dữ liệu: human labels, empty review queue và rates khi thiếu traffic có thể No data/NaN. Simulation cố tình tạo drift/performance degradation, được đánh dấu synthetic. Dashboard là quyền quản trị nền tảng; tenant filter áp dụng SQL.

## Recovery và deployment

- Restore drill 28/09: `data/backups/ddm501_restore_drill_20260928_102822.dump`, **563.959 bytes**. Restore vào DB tạm riêng, đối chiếu số dòng của tám bảng, xóa DB tạm; không restore đè dữ liệu gốc.
- Rollback rehearsal thành công **8 → 7 → 8**, readiness được kiểm tra. Đây là bằng chứng trước khi champion 9 đăng ký, không gọi nhầm là rollback version 9.
- Portable serving image đã kiểm chứng local không có bind mount model, 19 integration checks pass, dùng chung local DB/MLflow/MinIO. Private overlay đã validate config. Chưa phải deployment cloud/customer thực tế.
- Load smoke trước đó: 20 requests, concurrency 2, 0 lỗi, p95 0,244s trên CPU warm; không suy ra SLA hoặc capacity production.

## CI/CD thực tế

Run [36430718832](https://github.com/TrinhDucDuong/ddm501-face-voice-proctoring/actions/runs/36430718832) **success**, commit `3e98c770c913b84f30e68e541d044551f966503c`, ngày 28/09/2026. Cả ba jobs **quality, containers, deploy-demo** thành công, gồm kiểm chứng dashboard/protected reports/freshness và upload artifacts. Remote: **52 passed, coverage 88,69%**; local: **52 passed, coverage 88,76%**. Deploy thực tế trên Docker Desktop qua runner Windows, source release ngoài OneDrive, dữ liệu/secrets giữ nguyên; chưa phải public cloud deployment.

Quality: Ruff → compile → dashboard consistency → pytest/coverage ≥80% → Compose config. Containers: build API/UI/drift/ops/Airflow/webhook/legacy trên GitHub Ubuntu. Deploy: trusted-main runner Windows, giữ dữ liệu/secrets/weights → Compose rollout → readiness/monitoring smoke → dashboard queries/protected reports/freshness. Artifacts: `quality-evidence` (JUnit/coverage XML), `deployment-monitoring-evidence`.

Các lỗi thực tế đã sửa: Ruff mới thay đổi defaults (pin phiên bản/cấu hình rules); Windows execution policy chặn Python setup và scripts (runtime Python + process-scoped bypass); Docker Desktop không đọc được file bind từ checkout OneDrive (Git archive đúng SHA sang release ngoài OneDrive, probe file config đọc thành công). Không thay policy toàn máy. Runner chạy theo phiên, cần khởi động lại sau reboot; xem [OPERATIONS.md](OPERATIONS.md).

## Giới hạn còn mở

Evaluation đã identity-disjoint trong tập demo, nhưng face/voice bootstrap ghép tổng hợp; genuine inference dùng lại media enroll. Chưa chứng minh chất lượng trên người dùng mới, fairness demographic, liveness hay audio anti-spoof. Cần consented real data/human labels; không dùng synthetic để đạt human gate. Camera/mic cần browser acceptance thực tế. Team contribution/demo/Q&A cần người thật. Repo đã xác minh public qua GitHub API ngày 28/09. Cloud/TLS/SSO/customer deployment chưa triển khai.

## Xem trực tiếp

- [Grafana Monitoring Centre](http://localhost:13000/d/biometric-overview)
- [Portal](http://localhost:18501), [legacy exam](http://localhost:18600), [API docs](http://localhost:18100/docs)
- [Airflow](http://localhost:18081), [MLflow](http://localhost:15030), [MinIO](http://localhost:19101)
- [Prometheus targets](http://localhost:19090/targets), [alerts](http://localhost:19090/alerts), [Alertmanager](http://localhost:19093)
- [Telegram bot](https://t.me/ddm501_face_voice_proctoring_bot)
- Đầy đủ URL report/exporters/health và trạng thái runtime: [PROJECT_STATE.md](PROJECT_STATE.md).
