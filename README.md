# DDM501 - Face & Voice Integrity Service

D?ch v? x?c minh face/voice theo batch cho doanh nghi?p t? ch?c ??nh gi? ngo?i ng? th??ng ni?n. H? th?ng c?ng ty gi? b?i thi, l?ch capture, ?i?m v? quy?t ??nh nghi?p v?. D? ?n cung c?p API/webhook, portal c?ng ty v? full pipeline MLOps m?n h?c.

## Hai kh?ng gian v?n h?nh

- C?ng ty: ??ng k? g?i gi? l?p, qu?n l? nh?n vi?n, ghi danh qua camera/audio/upload ho?c API, c?p integration key, webhook, check history, b?ng ch?ng nghi v?n, PDF/CSV.
- N?n t?ng: Airflow/MLflow/CI-CD v? Grafana/Evidently/Telegram. Tenant portal kh?ng c?p quy?n truy c?p monitoring to?n h? th?ng.

## Demo

Portal http://localhost:18501; customer integration example http://localhost:18600; API http://localhost:18100/docs.
Grafana http://localhost:13000/d/biometric-overview; Airflow http://localhost:18081; MLflow http://localhost:15030; MinIO http://localhost:19101.

??ng k? c?ng ty ? portal khi ch?a ??ng nh?p, l?u operator key ???c tr? m?t l?n. Ghi danh >=2 ?nh/WAV, t?o integration key v? c?u h?nh webhook. Backend g?i POST /v1/checks v?i person_id, session_id, request_id, consent, face_file v? voice_file. V? d? 30 gi?y/?nh v? 10 gi?y/audio l? cadence ph?a kh?ch h?ng.

## Model v? b?ng ch?ng

YuNet/SFace + ECAPA x?c minh 1:1. MiniFASNet face PAD v? AASIST audio anti-spoof l? detector nghi?n c?u pretrained/pinned; ECAPA segments l? heuristic thay ng??i n?i. K?t qu? verified/suspicious/inconclusive th? hi?n ki?m tra ?? th?c hi?n. Ch?a ch?ng minh m?i deepfake, physical replay ho?c simultaneous speakers. Missing detector kh?ng ???c coi passed.

PostgreSQL l?u embedding/metadata/checks. MinIO gi? suspicious image/WAV v? MLflow artifacts. Raw enrollment v? media checks h?p l? m?c ??nh kh?ng gi?. Tenant isolation ?p d?ng c? l?ch s?, export v? evidence download. Webhook HMAC c? durable outbox/retry; receiver deduplicates.

## Ch?y v? ki?m ch?ng

Kh?ng overwrite .env ?? c? v? kh?ng down -v. Xem PROJECT_STATE.md v? deployment ngo?i OneDrive v? runtime paths.

```powershell
docker compose up -d --build --wait
python pipeline/verify_company_service.py
python pipeline/verify_monitoring_centre.py
```

[Report d? ?n](PROJECT_REPORT.md) ? [Scope](PROJECT_REQUIREMENTS.md) ? [Ki?n tr?c](ARCHITECTURE.md) ? [API integration](SAAS_INTEGRATION.md) ? [Mapping rubric/pipeline](RUBRIC_MAPPING.md) ? [B?ng ch?ng](VERIFICATION.md) ? [V?n h?nh](OPERATIONS.md) ? [Gi?i h?n](RESPONSIBLE_AI.md).

GitHub: https://github.com/TrinhDucDuong/ddm501-face-voice-proctoring. Grafana/Airflow demo admin/admin, loopback only. Kh?ng ??a secrets/keys/media/backup v?o Git.
