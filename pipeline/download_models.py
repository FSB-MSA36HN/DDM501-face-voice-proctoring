"""Download immutable model revisions from Hugging Face Hub."""
import os
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(Path(__file__).resolve().parents[1] / "models")))
MODEL_DIR.mkdir(parents=True, exist_ok=True)

if os.getenv("OFFLINE_MODE", "false").lower() == "true":
    required = ["face_recognition_sface_2021dec.onnx", "face_detection_yunet_2023mar.onnx"]
    required += ["speechbrain-ecapa/" + name for name in (
        "hyperparams.yaml", "embedding_model.ckpt", "classifier.ckpt", "mean_var_norm_emb.ckpt", "label_encoder.txt",
    )]
    missing = [name for name in required if not (MODEL_DIR / name).is_file()]
    if missing:
        raise RuntimeError("Offline model files missing: " + ", ".join(missing))
    print("Offline mode: using pre-provisioned local weights")
    sys.exit(0)

FILES = [
    ("opencv/face_recognition_sface", "face_recognition_sface_2021dec.onnx", "3d7082438a6e4551e840c9b2bb60b71e8da4b524"),
    ("opencv/face_detection_yunet", "face_detection_yunet_2023mar.onnx", "3cc26e7f1014a5ee5d74a42acee58bafc9d0a310"),
]

for repo_id, filename, revision in FILES:
    path = hf_hub_download(repo_id=repo_id, filename=filename, revision=revision, local_dir=MODEL_DIR)
    print(f"downloaded {repo_id}@{revision}: {path}")

voice_dir = snapshot_download(
    repo_id="speechbrain/spkrec-ecapa-voxceleb",
    revision="0f99f2d0ebe89ac095bcc5903c4dd8f72b367286",
    local_dir=MODEL_DIR / "speechbrain-ecapa",
    allow_patterns=["*.yaml", "*.ckpt", "*.txt", "*.json"],
)
print(f"downloaded SpeechBrain ECAPA: {voice_dir}")
