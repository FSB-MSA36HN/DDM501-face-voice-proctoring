# Kiến trúc tổng quan — DDM501 Face & Voice Integrity

Dự án hiện chạy bằng **Docker Compose trên một máy**, chưa dùng Kubernetes hoặc `node_exporter`. Hệ thống thi của công ty đứng ngoài **nền tảng MLOps DDM501**; bên trong nền tảng là serving, vòng đời model, monitoring/vận hành và CI/CD.

```mermaid
flowchart LR
    subgraph KH["Công ty khách hàng"]
        EXAM["Hệ thống thi<br/>chọn thời điểm gửi ảnh/WAV<br/>giữ điểm và quyết định nghiệp vụ"]
        ADMIN["Quản trị công ty"]
    end

    subgraph PLATFORM["Nền tảng MLOps DDM501 — Docker Compose"]
    subgraph DV["Serving — dịch vụ xác minh cho công ty"]
        PORTAL["Portal riêng từng công ty<br/>nhân viên, ghi danh, lịch sử<br/>bằng chứng, PDF/CSV"]
        API["FastAPI<br/>POST /v1/checks"]
        IDMODEL["Xác minh danh tính 1:1<br/>YuNet/SFace + ECAPA"]
        INTEGRITY["Tín hiệu integrity<br/>nhiều mặt, PAD, AASIST<br/>thay giọng, dùng lại media"]
        DB[("PostgreSQL<br/>tenant, embedding, check<br/>event, webhook outbox")]
        S3[("MinIO<br/>bằng chứng nghi vấn<br/>MLflow artifacts")]
        WEBHOOK["Webhook worker<br/>HMAC + retry"]
    end

    subgraph ML["Vòng đời model — Airflow và MLflow"]
        AIRFLOW["Airflow DAG<br/>theo lịch hoặc chạy thủ công"]
        SNAP["1. Snapshot có phiên bản<br/>fingerprint SHA-256"]
        DQ["2. Data quality gate<br/>kiểm tra mẫu và embedding"]
        TRAIN["3. Feature pairs + calibration<br/>CV theo identity, holdout riêng"]
        CAND["MLflow candidate<br/>params, metrics, artifacts"]
        RAI["4. Responsible AI audit<br/>human/synthetic tách riêng"]
        GATE["5. Promotion gate<br/>FAR/FRR + counts + fingerprint"]
        CHAMP["MLflow champion<br/>identity policy / thresholds"]
        KEEP["Không đạt gate<br/>giữ champion đang phục vụ"]
        RELOAD["6. Reload champion<br/>qua API quản trị"]
    end

    subgraph OPS["Monitoring và vận hành"]
        DRIFT["drift-monitor<br/>PSI + Evidently<br/>human/synthetic feedback"]
        OPM["ops-monitor<br/>readiness, data quality<br/>Registry, DAG, RAI, Docker stats"]
        PROXY["Docker socket proxy<br/>chỉ đọc, POST=0"]
        ALLOY["Alloy"]
        LOKI["Loki<br/>container logs"]
        PROM["Prometheus<br/>pull /metrics + alert rules"]
        GRAFANA["Grafana<br/>dashboard trung tâm"]
        REPORTS["HTML/JSON reports<br/>Evidently + vận hành"]
        GATEWAY["Grafana gateway<br/>report cùng origin<br/>yêu cầu đăng nhập"]
        ALERT["Alertmanager"]
        TELEGRAM["Telegram<br/>cảnh báo kỹ thuật nền tảng"]
        OPERATOR["Đội vận hành<br/>xem xét cảnh báo và kết quả"]
    end

    subgraph CD["CI/CD — triển khai nền tảng"]
        CI["GitHub Actions + runner Windows<br/>quality → build → deploy"]
    end
    end

    ADMIN --> PORTAL --> API
    EXAM -->|"Ảnh + WAV theo batch do công ty chọn"| API
    API -->|"Kết quả check ngay"| EXAM
    API --> IDMODEL
    API --> INTEGRITY
    API --> DB
    API -->|"Chỉ media của check nghi vấn"| S3
    DB -->|"Kết quả đã commit"| WEBHOOK
    WEBHOOK -->|"Signed webhook"| EXAM

    DB -->|"Snapshot: mặc định tenant demo"| AIRFLOW
    AIRFLOW --> SNAP --> DQ --> TRAIN --> CAND --> RAI --> GATE
    CAND -->|"Ghi artifacts"| S3
    GATE -->|"Đạt"| CHAMP --> RELOAD --> API
    GATE -->|"Không đạt"| KEEP

    DB -->|"Event / feedback"| DRIFT
    DB -->|"Data quality"| OPM
    CHAMP -->|"Version / evaluation"| OPM
    AIRFLOW -->|"Task / DAG status"| OPM
    PROXY -->|"Container stats"| OPM
    PROXY -->|"Container logs"| ALLOY --> LOKI
    DRIFT --> REPORTS
    OPM --> REPORTS
    PROM -->|"Scrape /metrics"| API
    PROM -->|"Scrape /metrics"| WEBHOOK
    PROM -->|"Scrape /metrics"| DRIFT
    PROM -->|"Scrape /metrics"| OPM
    GRAFANA -->|"Truy vấn metric"| PROM
    GRAFANA -->|"SQL"| DB
    GRAFANA -->|"Truy vấn log"| LOKI
    GRAFANA --> GATEWAY
    REPORTS --> GATEWAY
    PROM -->|"Firing / resolved"| ALERT -->|"Webhook"| OPM --> TELEGRAM
    GRAFANA -->|"Theo dõi / điều tra"| OPERATOR
    TELEGRAM -->|"Cảnh báo để xử lý"| OPERATOR
    OPERATOR -.->|"Sau khi đánh giá: chạy DAG thủ công"| AIRFLOW
    CI -->|"Triển khai stack"| DV
```

**Ranh giới nghiệp vụ:** công ty tự điều khiển lịch capture, bài thi, điểm và quyết định; DDM501 trả kết quả từng check ngay qua API và signed webhook. Portal chỉ hiển thị dữ liệu của công ty đó. Ảnh/audio của check thường không được lưu theo cấu hình mặc định; ảnh/audio nghi vấn được lưu làm bằng chứng trong MinIO.

**Vòng MLOps chung:** sáu bước đánh số là sáu task thực tế của DAG `biometric_model_pipeline`. Airflow hiệu chỉnh, đánh giá và promotion **identity policy**; serving dùng champion được nạp, còn monitoring quan sát dữ liệu/model/dịch vụ sau triển khai. MiniFASNet/AASIST là detector nghiên cứu có trọng số đã pin, chưa có benchmark anti-spoof trên dữ liệu khách hàng. Gate không đạt thì giữ champion đang phục vụ; MLflow quản lý Registry/artifacts, còn MinIO giữ artifact.

**Phản hồi vận hành:** Prometheus **chủ động kéo** metric từ API, webhook worker, drift-monitor và ops-monitor. Grafana truy vấn Prometheus, PostgreSQL và Loki; Alertmanager gửi sự kiện đến ops-monitor để chuyển cảnh báo kỹ thuật qua Telegram. Người vận hành xem xét rồi mới kích hoạt DAG nếu cần: cảnh báo **không tự động retrain**. Công ty không dùng Telegram này để nhận kết quả check. Docker stats đi qua proxy và ops-monitor; bản Compose hiện không có `node_exporter`.
