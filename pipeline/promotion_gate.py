"""Validate candidate metrics and promote the MLflow alias only when gates pass."""
from __future__ import annotations

import json
import os
import math

def gate(metrics: dict[str, float], max_error_rate: float = 0.20, min_pairs: int = 5, require_identity: bool = True) -> list[str]:
    failures = []
    for modality in ("face", "voice"):
        for metric in ("far", "frr", "cv_far", "cv_frr") + (("holdout_far", "holdout_frr") if require_identity else ()):
            value = metrics.get(f"{modality}_{metric}")
            if value is None or not math.isfinite(value) or not 0 <= value <= max_error_rate:
                failures.append(f"{modality}_{metric}={value} > {max_error_rate}")
        for metric in ("positive_pairs", "negative_pairs") + (("holdout_positive_pairs", "holdout_negative_pairs") if require_identity else ()):
            value = metrics.get(f"{modality}_{metric}", 0)
            if not math.isfinite(value) or value < min_pairs:
                failures.append(f"{modality}_{metric}={value} < {min_pairs}")
    return failures


def promote(client, model_name, candidate, expected_run_id=None):
    run = client.get_run(candidate.run_id)
    if expected_run_id and candidate.run_id != expected_run_id:
        raise RuntimeError('Candidate belongs to another pipeline run')
    failures = gate(run.data.metrics, float(os.getenv('MAX_BIOMETRIC_ERROR_RATE', '0.20')))
    if os.getenv('REQUIRE_HUMAN_FAIRNESS', 'false').lower() == 'true':
        report = json.loads(__import__('pathlib').Path(os.environ['RAI_REPORT']).read_text())
        if report.get('gate') != 'pass':
            failures.append('human fairness evidence is insufficient or rejected')
    result = {'model': model_name, 'candidate': candidate.version, 'metrics': run.data.metrics, 'failures': failures}
    print(json.dumps(result, indent=2))
    client.set_model_version_tag(model_name, candidate.version, 'promotion_status', 'rejected' if failures else 'passed')
    if failures:
        raise RuntimeError('candidate rejected by model validation gate')
    client.set_registered_model_alias(model_name, 'champion', candidate.version)
    return result


def main() -> None:  # pragma: no cover - exercised against MLflow in the Airflow integration test
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:15020"))
    model_name = os.getenv("MLFLOW_MODEL_NAME", "face-voice-risk-bundle")
    client = MlflowClient()
    candidate = client.get_model_version_by_alias(model_name, "candidate")
    run = client.get_run(candidate.run_id)
    if os.getenv('SNAPSHOT_PATH'):
        from data_snapshot import read_snapshot
        if run.data.params.get('dataset_version') != read_snapshot(os.environ['SNAPSHOT_PATH'])['dataset_version']:
            raise RuntimeError('Candidate snapshot does not match this DAG run')
    promote(client, model_name, candidate)


if __name__ == "__main__":
    main()
