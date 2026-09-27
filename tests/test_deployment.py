import pytest

from pipeline.prepare_deploy_env import prepare


def test_deploy_secrets_and_existing_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_POSTGRES_PASSWORD", "long_database_secret_501")
    monkeypatch.setenv("DEPLOY_API_KEY", "long_api_secret_501")
    (tmp_path / ".env.example").write_text(
        "POSTGRES_PASSWORD=biometric_dev_only\nAPI_KEY=demo-internal-key\n"
        "DATABASE_URL=postgresql://user:biometric_dev_only@postgres/db\nCUSTOM=keep\n"
    )
    prepare(tmp_path)
    content = (tmp_path / ".env").read_text()
    assert "user:long_database_secret_501@" in content
    assert "API_KEY=long_api_secret_501" in content
    assert "CUSTOM=keep" in content
    prepare(tmp_path)
    assert (tmp_path / ".env").read_text() == content
    monkeypatch.setenv("DEPLOY_POSTGRES_PASSWORD", "different_database_secret")
    with pytest.raises(ValueError, match="differs"):
        prepare(tmp_path)
    assert (tmp_path / ".env").read_text() == content


def test_deploy_rejects_missing_or_unsafe_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_POSTGRES_PASSWORD", "$(unsafe)/secret")
    with pytest.raises(ValueError, match="URL-safe"):
        prepare(tmp_path)
    assert not (tmp_path / ".env").exists()
