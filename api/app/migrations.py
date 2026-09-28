"""Additive migration for the pre-SaaS demo; safe to rerun without deleting records."""
from sqlalchemy import inspect, text


def migrate(engine) -> None:
    with engine.begin() as connection:
        # Serialize concurrent API startup migrations on PostgreSQL.
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(5012026)"))
        from . import models  # noqa: F401
        from .db import Base
        Base.metadata.create_all(connection)
        columns = {item["name"] for item in inspect(connection).get_columns("people")}
        if "tenant_id" not in columns:
            connection.execute(text("ALTER TABLE people ADD COLUMN tenant_id VARCHAR(36) NOT NULL DEFAULT 'demo'"))
            connection.execute(text("CREATE INDEX ix_people_tenant_id ON people (tenant_id)"))
        if "external_ref" not in columns:
            connection.execute(text("ALTER TABLE people ADD COLUMN external_ref VARCHAR(100)"))
        if "details" not in {item["name"] for item in inspect(connection).get_columns("audit_logs")}:
            connection.execute(text("ALTER TABLE audit_logs ADD COLUMN details TEXT"))
        connection.execute(text("INSERT INTO tenants (id, name, active, created_at) "
                                "VALUES ('demo', 'Existing demo', true, CURRENT_TIMESTAMP) ON CONFLICT (id) DO NOTHING"))
