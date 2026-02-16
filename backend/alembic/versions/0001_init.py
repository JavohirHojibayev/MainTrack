"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-10 13:40:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS minetrack")

    device_type = sa.Enum("HIKVISION", "ESMO", "TOOL_FACE", "MINE_FACE", "OTHER", name="device_type")
    event_type = sa.Enum(
        "TURNSTILE_IN",
        "TURNSTILE_OUT",
        "ESMO_OK",
        "ESMO_FAIL",
        "TOOL_TAKE",
        "TOOL_RETURN",
        "MINE_IN",
        "MINE_OUT",
        name="event_type",
    )
    event_status = sa.Enum("ACCEPTED", "REJECTED", name="event_status")

    device_type.create(op.get_bind(), checkfirst=True)
    event_type.create(op.get_bind(), checkfirst=True)
    event_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uq_users_username"),
        schema="minetrack",
    )

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_no", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=64), nullable=False),
        sa.Column("last_name", sa.String(length=64), nullable=False),
        sa.Column("patronymic", sa.String(length=64), nullable=True),
        sa.Column("department", sa.String(length=128), nullable=True),
        sa.Column("position", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("employee_no", name="uq_employees_employee_no"),
        schema="minetrack",
    )

    op.create_table(
        "employee_external_ids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("system", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["minetrack.employees.id"], name="fk_employee_external_ids_employee_id_employees"),
        sa.UniqueConstraint("system", "external_id", name="uq_employee_external_ids_system_external_id"),
        sa.UniqueConstraint("employee_id", "system", name="uq_employee_external_ids_employee_system"),
        schema="minetrack",
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("device_code", sa.String(length=64), nullable=False),
        sa.Column("device_type", device_type, nullable=False),
        sa.Column("location", sa.String(length=128), nullable=True),
        sa.Column("api_key", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_code", name="uq_devices_device_code"),
        sa.UniqueConstraint("api_key", name="uq_devices_api_key"),
        schema="minetrack",
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("event_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_id", sa.String(length=128), nullable=False),
        sa.Column("status", event_status, nullable=False),
        sa.Column("reject_reason", sa.String(length=255), nullable=True),
        sa.Column("source_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["minetrack.devices.id"], name="fk_events_device_id_devices"),
        sa.ForeignKeyConstraint(["employee_id"], ["minetrack.employees.id"], name="fk_events_employee_id_employees"),
        sa.UniqueConstraint("device_id", "raw_id", name="uq_events_device_raw_id"),
        schema="minetrack",
    )

    op.create_index("ix_events_event_ts", "events", ["event_ts"], schema="minetrack")
    op.create_index("ix_events_event_type", "events", ["event_type"], schema="minetrack")
    op.create_index("ix_events_employee_id", "events", ["employee_id"], schema="minetrack")

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["minetrack.users.id"], name="fk_audit_logs_user_id_users"),
        schema="minetrack",
    )


def downgrade() -> None:
    op.drop_table("audit_logs", schema="minetrack")
    op.drop_index("ix_events_employee_id", table_name="events", schema="minetrack")
    op.drop_index("ix_events_event_type", table_name="events", schema="minetrack")
    op.drop_index("ix_events_event_ts", table_name="events", schema="minetrack")
    op.drop_table("events", schema="minetrack")
    op.drop_table("devices", schema="minetrack")
    op.drop_table("employee_external_ids", schema="minetrack")
    op.drop_table("employees", schema="minetrack")
    op.drop_table("users", schema="minetrack")

    op.execute("DROP TYPE IF EXISTS event_status")
    op.execute("DROP TYPE IF EXISTS event_type")
    op.execute("DROP TYPE IF EXISTS device_type")
