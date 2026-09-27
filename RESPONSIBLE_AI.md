# Responsible AI and privacy

This is decision support. A mismatch becomes `REVIEW`, never an automatic accusation. Quality is not liveness, face PAD or voice anti-spoofing.

## Fairness

`pipeline/responsible_ai_report.py` measures accuracy/FAR/FRR across low, medium and high capture-quality slices after proctors submit labels. A >10-point accuracy gap is flagged for review once each comparable slice has at least 20 labels. This detects an operational harm pathway (devices/network/environment), but it is not demographic fairness. The synthetic LFW + Speech Commands pairing has no valid demographic labels, so the project makes no demographic parity claim. A production pilot must collect optional, consented, purpose-limited evaluation labels and report intersectional FAR/FRR with confidence intervals before launch.

Mitigations include multi-sample enrollment, explicit image/audio quality gates, two modalities, no automatic rejection, slice monitoring, accessible re-capture and manual appeal.

## Explainability

Every response and audit event contains face/voice scores, quality values, thresholds, model version and human-readable policy reason codes. These local, faithful explanations are more appropriate for a deterministic threshold policy than post-hoc SHAP/LIME. The MLflow artifact records threshold selection and evaluation metrics.

## Privacy and ethics

SaaS sessions record explicit consent time before verification. Tenant queries and credentials are scoped; platform monitoring pages are admin-only. New customer templates do not enter default training (`TRAINING_TENANT_ID=demo`). Manual approval/rejection is audited separately from the model prediction, preserving performance evaluation integrity. API keys are hashed, session tokens are not placed in query strings/access logs, and webhook payloads contain no media/templates.

Synthetic simulation labels are identified separately in the quality-slice report. FAR uses impostor count as denominator, FRR uses genuine count; missing classes produce null rates. The human fairness gate returns `insufficient_data` until enough actual human-labelled slices exist. Do not rename simulation feedback as human review to make this gate pass.

- Biometric embeddings and media are sensitive personal data; obtain explicit consent and publish purpose/retention rules.
- Raw storage is disabled by default. Production requires TLS, KMS-backed encryption, secret management, SSO/RBAC, audit access and deletion/export workflows.
- Do not reuse data for surveillance or unrelated identification. This system supports 1:1 declared identity only.
- Limit retention for raw samples, templates and events separately; document lawful basis and incident response.
- Known risks include demographic performance gaps, disability/accent effects, replay/deepfake attacks, coercion and over-reliance by proctors.
