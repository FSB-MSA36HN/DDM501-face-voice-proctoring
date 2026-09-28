"""Reuse authorized local persistence/secrets from a trusted Windows runner checkout."""
import os
from pathlib import Path

from dotenv import dotenv_values, set_key


def prepare(destination, runtime):
    runtime = runtime.resolve()
    source = runtime / '.env'
    if not source.is_file():
        raise ValueError('Runner runtime .env is missing')
    config = dict(dotenv_values(source))
    for name, suffix in [('MODELS_PATH','models'),('DATA_PATH','data'),('REPORTS_PATH','reports'),('AIRFLOW_LOGS_PATH','airflow/logs')]:
        config[name] = (runtime / suffix).as_posix()
    # The self-hosted deployment retains the same DB credentials, named volumes
    # and biometric assets. Only trusted main-branch source code is replaced.
    target = destination / '.env'
    target.write_text('', encoding='utf-8')
    for name, value in config.items():
        if value is not None:
            set_key(target, name, value, quote_mode='always')
    target.chmod(0o600)


if __name__ == '__main__':
    prepare(Path.cwd(), Path(os.environ['DDM501_RUNTIME_ROOT']))
