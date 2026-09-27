# Model performance và CI/CD

## SaaS operation checkpoint

- Tenant operator dùng portal để xem phiên, xử lý REVIEW, xem audit và retry webhook đã thất bại. Không sửa kết quả dự đoán gốc khi có quyết định của người kiểm tra.
- Worker riêng xử lý outbox bền vững trong PostgreSQL. Theo dõi backlog/failed delivery trong Grafana và `http://localhost:18002/metrics`; khách hàng phải xử lý webhook idempotent.
- Trước migration SaaS đã lưu `data/backups/pre-saas-20260927.dump`. Không tự restore đè dữ liệu đang chạy; xem quy trình backup/rollback trong [DEPLOYMENT.md](DEPLOYMENT.md).
- Local CI: `powershell -ExecutionPolicy Bypass -File pipeline/ci_local.ps1`. Đây không phải bằng chứng GitHub Actions/self-hosted runner đã chạy.
- Kiểm tra tích hợp: `python pipeline/verify_saas.py`; tạo thêm các phiên/event demo, không xóa dữ liệu cũ. Credential demo nằm trong `data/local-saas.json`, không gửi vào log hoặc commit.
- Toàn bộ URL pipeline nằm ở [PROJECT_STATE.md](PROJECT_STATE.md); link monitoring chỉ được hiển thị cho platform admin trong portal. Khi triển khai public cần bảo vệ cả các dịch vụ monitoring phía reverse proxy/SSO, không chỉ ẩn link UI.

## Evidently performance

`drift-monitor` tạo `reports/model-performance.html` bằng Evidently 0.4.40 `ClassificationPreset`, gồm accuracy, precision, recall, F1 và confusion matrix. Summary ở `reports/model-performance.json`. Report data drift vẫn ở `reports/data-drift.html`.

Ground truth lấy từ `verification_feedback.is_genuine`, prediction từ `verification_events.accepted`, join bằng event ID. Positive class là người thật (`1`). `REVIEW` được tính là không accept, không phải kết luận gian lận. Chỉ đánh giá các event đã được giám thị gắn nhãn; đây là performance trên tập reviewed, có thể không đại diện toàn bộ traffic.

Hai cửa sổ không giao nhau, sắp theo thời gian inference, mỗi cửa sổ `PERFORMANCE_WINDOW_SIZE` event có feedback (mặc định 100). Reference là cửa sổ trước, current là cửa sổ mới nhất. Cần cả genuine và impostor trong mỗi cửa sổ. Khi chưa đủ nhãn hoặc thiếu một lớp, report hiển thị trạng thái chờ; không tạo nhãn giả. Performance được tính độc lập trước bước data drift nên vẫn có report nếu drift chưa đủ dữ liệu.

Trong `.env`, có thể giảm `PERFORMANCE_WINDOW_SIZE=10` cho demo (cần ít nhất 20 event được review và đủ hai lớp mỗi cửa sổ). Sau khi thay cấu hình, chạy:

```powershell
docker compose up -d --build drift-monitor
```

Gắn nhãn qua UI hoặc `PUT /v1/events/{event_id}/feedback`. Sau một chu kỳ monitor (mặc định 60 giây), mở HTML và Grafana panel **Evidently model performance (reviewed events)**. `biometric_model_performance{metric,window}` chứa các metric; `biometric_performance_report_success` bằng 1 khi report thành công, 0 khi chờ/lỗi. Cảnh báo `BiometricPerformanceDegraded` bật nếu current accuracy <80% trong 5 phút và report đang hợp lệ. Ngưỡng demo này chỉnh trong `monitoring/prometheus/alerts.yml`.

## Kiểm chứng Docker end-to-end

Kết quả chạy thực tế: [VERIFICATION.md](VERIFICATION.md). Có thể kiểm chứng lại stack hiện tại bằng:

```powershell
python pipeline/verify_stack.py --dag-run verification_20260927_gatefix --inference --require-alerts
```

Lệnh ghi bằng chứng vào `reports/verification.json`. `--inference` gửi hai request ảnh/WAV thật từ bootstrap đã enroll (cùng và khác danh tính), tạo thêm verification events. `--require-alerts` yêu cầu cả drift/performance alert đang firing và đã tới Alertmanager.

Để tạo lại kịch bản monitoring có ground truth kỹ thuật:

```powershell
python pipeline/simulate_drift.py --samples 100 --with-feedback
```

Lệnh tạo 200 observations và feedback tổng hợp, gắn reviewer `synthetic-simulation`; không phải nhãn do giám thị xác nhận. Reference được thiết kế đúng, current cố tình sai để chứng minh cảnh báo hoạt động. Chờ một chu kỳ monitor và ít nhất 5 phút để performance alert chuyển sang firing. Không dùng kết quả này để báo cáo độ chính xác sinh trắc học ngoài thực tế.

Airflow snapshot hiện lưu chính xác feature rows và fingerprint cho từng run. MLflow lưu `data/snapshot.json`, `data/validation.json` và `dataset_version`. Gate kiểm tra FAR/FRR trên calibration và cross-validation; nếu bị reject, kiểm tra metrics trước khi sửa model/dữ liệu, không nới gate chỉ để DAG xanh.

## Auto-deploy trên GitHub

Workflow `.github/workflows/ci.yml` chạy lint, tests (bao gồm tạo report Evidently thật), coverage >80%, Compose validation và container builds. Push/merge vào `main` tự chạy deploy sau khi các quality/build jobs thành công. Push `develop` và pull request chỉ chạy CI. Vẫn có thể chạy `workflow_dispatch` với `deploy=true` trên `main`.

Thiết lập một lần trên GitHub repo:

1. Trong Settings → Actions → Runners, đăng ký runner Linux riêng cho demo, có labels `self-hosted`, `linux`, `ddm501-demo`; cài Docker Engine, Docker Compose v2 và curl. Runner cần quyền Docker, internet và đủ tài nguyên để build model images.
2. Tạo environment `demo`, cho phép deploy từ `main`. Nếu muốn hoàn toàn tự động, environment không được yêu cầu manual approval.
3. Thêm environment secrets `POSTGRES_PASSWORD` và `API_KEY`, mỗi giá trị ít nhất 16 ký tự thuộc `A-Z`, `a-z`, `0-9`, `_`, `-`. Với DB đã tồn tại, mật khẩu phải trùng mật khẩu DB đang dùng; workflow không tự đổi mật khẩu DB.
4. Đưa các thay đổi đã kiểm tra lên `main`, xem job `deploy-demo` và các smoke tests API, exporter, Prometheus, Grafana.

Deploy jobs chạy tuần tự, không hủy deploy đang chạy. Checkout giữ file runtime như `.env`, models và reports. Không dùng runner demo này để chạy PR không tin cậy. `prepare_deploy_env.py` đọc secrets qua environment, không in giá trị và giữ cấu hình `.env` hiện có; nếu mật khẩu DB thay đổi thì dừng để tránh làm mất kết nối dữ liệu cũ.

Các cổng service bind loopback: truy cập từ máy runner hoặc qua SSH tunnel. GitHub-hosted CI không triển khai dịch vụ lên máy Windows đang mở workspace. Workflow chưa có tự động rollback; nếu smoke test thất bại, kiểm tra `docker compose ps` và logs, sửa lỗi hoặc revert commit trên `main` để chạy lại deployment.

## Kiểm tra tại máy phát triển

```powershell
pip install -r requirements-api.txt -r requirements-monitoring.txt pytest pytest-cov ruff
python -m ruff check api pipeline monitoring tests
python -m pytest --cov=app.biometrics --cov=app.decision --cov=pipeline.validate_data --cov=pipeline.promotion_gate --cov=monitoring.drift_monitor --cov-report=term-missing --cov-fail-under=80
docker compose config --quiet
```

API Evidently tham khảo: [Classification Performance](https://docs-old.evidentlyai.com/presets/class-performance).
