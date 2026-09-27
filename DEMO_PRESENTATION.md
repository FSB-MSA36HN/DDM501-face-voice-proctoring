# Kịch bản thuyết trình 15–20 phút

1. **2 phút — Vấn đề/giải pháp:** xác minh 1:1 trong thi online, phần mềm cũ không cần thay thế, SaaS API/hosted verification và private option.
2. **3 phút — Kiến trúc:** tenant isolation, session binding, PostgreSQL transaction/outbox, HMAC webhook, người review; tách control plane MLflow/Airflow khỏi serving.
3. **4 phút — Demo tích hợp:** mở :18600, chọn DEMO-001, tạo phiên; thử vào thi trước verify bị chặn; mở hosted page, upload media demo đúng; xem webhook nhận và vào thi một lần. Thử media DEMO-002 → review → operator reject.
4. **3 phút — ML pipeline:** mở Airflow run `saas_tenant_scope_20260927`; 6 tasks success. MLflow run có snapshot fingerprint/validation, threshold-grid experiment, pair CV, candidate/champion; API model version khớp Registry.
5. **3 phút — Monitoring:** Grafana metrics/latency/webhook; Evidently drift và classification; Prometheus firing → Alertmanager. Giải thích reference/current window và synthetic feedback cố tình làm performance giảm.
6. **2 phút — Chất lượng/vận hành:** tests/coverage, local CI, GitHub workflow/runner prerequisite, container weights packaged, backup/migration, sample CPU load test.
7. **2 phút — Responsible AI/giới hạn:** review không phải kết luận gian lận; chưa liveness/deepfake; chất lượng capture không phải demographic fairness; synthetic labels không chứng minh accuracy ngoài thực tế; consent/privacy.

## Câu hỏi nên chuẩn bị

- Tại sao SaaS và PaaS không phải hai lựa chọn loại trừ nhau?
- Không sửa phần mềm cũ thì enforce verify được không? (Không; backend đối tác phải tham gia.)
- Client giả mạo `success=true` hoặc gửi lại callback có vào thi được không?
- Nếu callback đến lặp/trễ/ngược thứ tự hoặc worker chết thì xử lý thế nào?
- Dữ liệu tenant A có vào training/model monitoring tenant B không? (Training mặc định chỉ demo; operational monitoring toàn nền tảng chỉ admin được xem.)
- Vì sao tune ngưỡng thay vì train SFace/ECAPA từ đầu? CV ở cấp pair có giới hạn gì?
- Rủi ro replay/deepfake khác replay giao thức ra sao?
- Vì sao test demo media score 1.0 không phải bằng chứng chất lượng model?

## Phần nhóm phải hoàn tất trước nộp

- Điền tên, trách nhiệm thật trong CONTRIBUTING.md; mỗi thành viên commit phần mình làm và hiểu được nội dung.
- Tạo slide PowerPoint/Google Slides/Canva dựa trên kịch bản; mọi thành viên tham gia demo/Q&A.
- Push code đã review; chạy GitHub Actions trên runner đã cấu hình; lưu link run/evidence.
- Public repo hoặc cấp giảng viên quyền truy cập. Không push `.env`, keys, biometric dataset hay backups.
