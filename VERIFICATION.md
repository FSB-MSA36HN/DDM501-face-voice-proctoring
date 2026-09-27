# Kiểm chứng MLOps full pipeline — 27/09/2026 (Asia/Saigon)

Đã chạy trên Docker Desktop Linux engine 29.7.2. Bằng chứng máy đọc được: `reports/verification.json`; báo cáo Evidently: `reports/data-drift.html` và `reports/model-performance.html` (runtime artifacts được gitignore).

| Hạng mục | Kết quả thực tế |
|---|---|
| Airflow | Run `saas_tenant_scope_20260927`: 6/6 tasks success, bao gồm reload API |
| Data → training | 282 feature samples; snapshot cố định theo run, fingerprint được kiểm tra trước training |
| MLflow lineage | Champion version 7; có `dataset_version`, `training_tenant_scope=demo`, `data/snapshot.json`, `data/validation.json` |
| Evaluation | Voice calibration FAR 16,08%, FRR 14,19%; CV FAR 15,69%, FRR 16,23%; face CV FAR 0,82%, FRR 0%; tất cả dưới gate 20% |
| Serving | API backend `pretrained`, version 7; tự tải đúng champion sau recreate container |
| Inference ảnh/WAV | Bootstrap cùng danh tính: allow (score 1/1); khác danh tính: review (face 0,1949, voice 0,1087) |
| Latency mẫu kiểm tra | Cold request 3.181 ms; request tiếp theo 84 ms — không phải load test/SLA |
| Prometheus | `biometric-api`, `drift-monitor`, `webhook-worker` scrape UP; 8 series performance (4 metrics × 2 windows) |
| Grafana | Dashboard được provision, có 12 panels bao gồm Evidently performance và webhook/outbox |
| Evidently | HTML/JSON drift và classification được tạo thật; simulation reference accuracy 1, current 0 |
| Alerts | `BiometricDataDrift`, `BiometricPerformanceDegraded` firing và có trong Alertmanager; review-rate phụ thuộc cửa sổ traffic |
| Tests | 34 passed; core coverage 84,85%; Ruff, Compose local/private config, 8 Prometheus rules và diff checks pass |

## SaaS / portable serving evidence

- `reports/saas-verification.json`: 19 kiểm tra live pass sau rebuild API/worker. Bao gồm tenant isolation, verify genuine/impostor bằng ảnh/WAV, token dùng một lần, consent, REVIEW/reject, callback HMAC và quyền vào bài thi chỉ một lần.
- `reports/paas-verification.json`: 19 kiểm tra tích hợp trên image `ddm501-saas-serving:local`, weights được đóng gói sẵn, container không có bind mount/volume. Đây là kiểm tra tính di chuyển local với PostgreSQL/MLflow/MinIO dùng chung, không phải đã deploy lên nhà cung cấp PaaS.
- `reports/load-test.json`: 20 requests, concurrency 2, 0 lỗi, p95 0,244 giây trên CPU đã warm. Không đại diện SLA, cold start, tải nhiều tenant hay độ chính xác biometric thực tế.
- Migration giữ nguyên dữ liệu cũ; backup trước migration tại `data/backups/pre-saas-20260927.dump`. Kiểm thử migration chạy lại được và không mất hồ sơ cũ.
- Báo cáo RAI ở `data/reports/responsible-ai.json` tách nhãn human/synthetic. Gate `insufficient_data` do chưa đủ dữ liệu human; không công bố đã đạt demographic fairness.
- Private overlay đã validate cấu hình; HTTPS, secret thật, máy khách và hạ tầng cloud chưa được triển khai. Hosted camera/microphone cần kiểm thử trình duyệt với người dùng thật; API upload media đã được kiểm chứng.

## Lỗi phát hiện và đã sửa khi chạy

- Run `verification_20260927` bị gate chặn đúng vì voice FRR 20,27%. Mục tiêu calibration ban đầu tối ưu trung bình FAR/FRR, không khớp gate từng chỉ số. Đã chuyển sang tối thiểu hóa chỉ số lỗi lớn nhất, giữ gate 20% và bổ sung kiểm tra CV FAR/FRR; run mới pass. Không xóa run thất bại.
- Snapshot trước đây chỉ chứa thống kê và không được training dùng trực tiếp. Đã cố định feature rows, kiểm tra fingerprint, dùng chung snapshot cho validation/calibration và log lineage vào MLflow.
- SpeechBrain vẫn tham chiếu Hub trong hyperparameters dù weights đã nằm local, làm request inference bị chờ. Đã override `pretrained_path` tới thư mục local; inference ảnh/WAV pass sau rebuild.
- API khởi động từng quay về threshold mặc định: đã tự tải champion và pin artifact theo version. Các phép tính embedding được chuyển sang threadpool để không chặn event loop của metrics/health.
- Cosine có miền [-1,1], nhưng policy chỉ nhận [0,1]: đã sửa miền hợp lệ và thêm regression test để negative cosine trả mismatch, không gây server error.

## Phạm vi bằng chứng

Đây là kiểm chứng kỹ thuật trên demo local. Face/voice bootstrap được ghép tổng hợp; mẫu cùng danh tính dùng lại media đã enroll. CV chia theo pairs, chưa identity-disjoint. Các kết quả trên không chứng minh độ chính xác trên người dùng mới. Feedback simulation được ghi rõ nguồn tổng hợp; cảnh báo hiện tại là kết quả cố ý tạo lỗi.

CI/CD workflow đã cấu hình auto-deploy `main`, nhưng chưa push/kiểm chứng job GitHub hoặc self-hosted runner. Alertmanager đã nhận alert; chưa có kênh gửi email/webhook bên ngoài. Các giới hạn này không được tính là đã kiểm chứng.

## Xem trực tiếp

- UI: http://localhost:18501
- API: http://localhost:18100/docs
- Airflow: http://localhost:18081
- MLflow: http://localhost:15030
- Grafana: http://localhost:13000/d/biometric-overview
- Prometheus: http://localhost:19090/alerts
- Alertmanager: http://localhost:19093
