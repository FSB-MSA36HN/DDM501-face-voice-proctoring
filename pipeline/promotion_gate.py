"""Validate candidate metrics and promote the MLflow alias only when gates pass."""
from __future__ import annotations

import json
import os
import math

def gate(metrics: dict[str, float], max_error_rate: float = 0.20, min_pairs: int = 5) -> list[str]:
    failures = []
    for modality in ("face", "voice"):
        for metric in ("far", "frr", "cv_far", "cv_frr"):
            value = metrics.get(f"{modality}_{metric}")
            if value is None or not math.isfinite(value) or value > max_error_rate:
                failures.append(f"{modality}_{metric}={value} > {max_error_rate}")
        for metric in ("positive_pairs", "negative_pairs"):
            value = metrics.get(f"{modality}_{metric}", 0)
            if value < min_pairs:
                failures.append(f"{modality}_{metric}={value} < {min_pairs}")
    return failures


def main() -> None:  # pragma: no cover - exercised against MLflow in the Airflow integration test
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:15020"))
    model_name = os.getenv("MLFLOW_MODEL_NAME", "face-voice-risk-bundle")
    client = MlflowClient()
    candidate = client.get_model_version_by_alias(model_name, "candidate")
    run = client.get_run(candidate.run_id)
    failures = gate(run.data.metrics, float(os.getenv("MAX_BIOMETRIC_ERROR_RATE", "0.20")))
    result = {"model": model_name, "candidate": candidate.version, "metrics": run.data.metrics, "failures": failures}
    print(json.dumps(result, indent=2))
    if failures:
        raise RuntimeError("candidate rejected by model validation gate")
    client.set_registered_model_alias(model_name, "champion", candidate.version)


if __name__ == "__main__":
    main()
