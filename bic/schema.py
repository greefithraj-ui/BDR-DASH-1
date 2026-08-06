"""BIC database schema: DDL definitions and forward-only migrations.

Implements the frozen Database Schema Review v2 (Sprint 2 T1). Every object is
created inside the BIC schema; BIC never creates or modifies objects outside
it. All enums below are frozen and must not be edited.
"""

import hashlib
import re
from dataclasses import dataclass

SCHEMA_NAME = "bic"

LIFECYCLE_STATES = (
    "OBSERVED",
    "TRACKING",
    "PENDING_REMOVAL",
    "FINALIZED",
)

END_REASONS = (
    "COMPLETED",
    "COMPLETED_FAILED",
    "REPLACED",
    "REMOVED",
    "TIMEOUT",
    "DECOMMISSIONED",
    "MANUAL_RESET",
    "UNKNOWN",
)

EVENT_TYPES = (
    "OBSERVED",
    "STATE_CHANGED",
    "ABSENT",
    "REAPPEARED",
    "CONFLICT",
    "REPLACED",
    "REMOVAL_PENDING",
    "FINALIZED",
    "OFFLINE",
    "MANUAL_RESET",
)

SCHEMA_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    checksum VARCHAR(128) NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by VARCHAR(128) NOT NULL
);
"""

_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_RESERVED_SCHEMAS = frozenset({"public", "pg_catalog", "information_schema"})


def validate_schema_name(name: str) -> str:
    """Return the name if it is a safe, non-reserved schema identifier."""
    if not isinstance(name, str) or _IDENTIFIER_RE.fullmatch(name) is None:
        raise ValueError(f"invalid schema name: {name!r}")
    if name in _RESERVED_SCHEMAS:
        raise ValueError(f"reserved schema not allowed: {name!r}")
    return name


def _sql_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _migration_1_sql() -> str:
    state_list = _sql_list(LIFECYCLE_STATES)
    reason_list = _sql_list(END_REASONS)
    event_list = _sql_list(EVENT_TYPES)
    return f"""
CREATE TABLE ring_identities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    serial_number VARCHAR(255) NOT NULL,
    ring_mac VARCHAR(32) NOT NULL,
    ring_name VARCHAR(128) NOT NULL,
    product VARCHAR(32) NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ring_identities_serial_number UNIQUE (serial_number)
);

CREATE INDEX idx_ring_identities_ring_mac ON ring_identities (ring_mac);

CREATE TABLE active_rings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ring_id BIGINT NOT NULL,
    machine_name VARCHAR(255) NOT NULL,
    slot_key VARCHAR(16) NOT NULL,
    serial_number VARCHAR(255) NOT NULL,
    state VARCHAR(32) NOT NULL DEFAULT 'OBSERVED',
    state_changed_at TIMESTAMPTZ NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    removal_confirmations INTEGER NOT NULL DEFAULT 0,
    removal_first_absent_at TIMESTAMPTZ NULL,
    firmware_version VARCHAR(100) NULL,
    end_reason VARCHAR(32) NULL,
    finalized_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_active_rings_ring_id FOREIGN KEY (ring_id) REFERENCES ring_identities (id),
    CONSTRAINT uq_active_rings_machine_slot UNIQUE (machine_name, slot_key),
    CONSTRAINT uq_active_rings_ring_id UNIQUE (ring_id),
    CONSTRAINT ck_active_rings_state CHECK (state IN ({state_list})),
    CONSTRAINT ck_active_rings_end_reason CHECK (end_reason IS NULL OR end_reason IN ({reason_list})),
    CONSTRAINT ck_active_rings_removal_confirmations CHECK (removal_confirmations >= 0)
);

CREATE INDEX idx_active_rings_serial_number ON active_rings (serial_number);
CREATE INDEX idx_active_rings_state_machine ON active_rings (state, machine_name);

CREATE TABLE ring_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ring_id BIGINT NOT NULL,
    machine_name VARCHAR(255) NOT NULL,
    slot_key VARCHAR(16) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NULL,
    reason VARCHAR(255) NULL,
    collector_version VARCHAR(32) NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'collector',
    CONSTRAINT fk_ring_events_ring_id FOREIGN KEY (ring_id) REFERENCES ring_identities (id),
    CONSTRAINT ck_ring_events_type CHECK (event_type IN ({event_list}))
);

CREATE INDEX idx_ring_events_ring_occurred ON ring_events (ring_id, occurred_at);
CREATE INDEX idx_ring_events_slot_occurred ON ring_events (machine_name, slot_key, occurred_at);
CREATE INDEX idx_ring_events_type_occurred ON ring_events (event_type, occurred_at);
CREATE INDEX idx_ring_events_occurred ON ring_events (occurred_at);

CREATE TABLE ring_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ring_id BIGINT NOT NULL,
    machine_name VARCHAR(255) NOT NULL,
    slot_key VARCHAR(16) NOT NULL,
    serial_number VARCHAR(255) NOT NULL,
    state_history JSONB NOT NULL,
    decision_summary JSONB NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    finalized_at TIMESTAMPTZ NOT NULL,
    end_reason VARCHAR(32) NOT NULL,
    firmware_version VARCHAR(100) NULL,
    collector_version VARCHAR(32) NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_ring_history_ring_id FOREIGN KEY (ring_id) REFERENCES ring_identities (id),
    CONSTRAINT ck_ring_history_end_reason CHECK (end_reason IN ({reason_list}))
);

CREATE INDEX idx_ring_history_serial_finalized ON ring_history (serial_number, finalized_at DESC);
CREATE INDEX idx_ring_history_ring_finalized ON ring_history (ring_id, finalized_at DESC);
CREATE INDEX idx_ring_history_slot_finalized ON ring_history (machine_name, slot_key, finalized_at DESC);
CREATE INDEX idx_ring_history_reason_finalized ON ring_history (end_reason, finalized_at);

CREATE TABLE machine_checkpoint (
    machine_name VARCHAR(255) PRIMARY KEY,
    last_rings_seen_at TIMESTAMPTZ NULL,
    last_bdr_seen_at TIMESTAMPTZ NULL,
    last_processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_offline BOOLEAN NOT NULL DEFAULT FALSE,
    last_offline_at TIMESTAMPTZ NULL,
    payload_checksum VARCHAR(128) NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    sql: str

    @property
    def checksum(self) -> str:
        return migration_checksum(self.sql)


def migration_checksum(sql: str) -> str:
    """Stable sha256 of a migration's SQL, used for ledger drift detection."""
    return hashlib.sha256(sql.strip().encode("utf-8")).hexdigest()


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        description="Initial BIC schema: ring_identities, active_rings, "
        "ring_events, ring_history, machine_checkpoint",
        sql=_migration_1_sql(),
    ),
)


def latest_schema_version() -> int:
    return max(migration.version for migration in MIGRATIONS)


def _set_search_path(conn, schema_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT set_config('search_path', %s, false)", (schema_name,))


def ensure_ledger(conn, schema_name: str = SCHEMA_NAME) -> None:
    """Create the schema and the schema_version ledger if they do not exist."""
    validate_schema_name(schema_name)
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
        _set_search_path(conn, schema_name)
        cur.execute(SCHEMA_VERSION_DDL)
    conn.commit()


def _ledger_exists(conn, schema_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = 'schema_version' "
            "AND table_type = 'BASE TABLE'",
            (schema_name,),
        )
        return cur.fetchone() is not None


def applied_migrations(conn, schema_name: str = SCHEMA_NAME) -> list[tuple]:
    """Return (version, description, checksum, applied_by, applied_at) rows."""
    validate_schema_name(schema_name)
    _set_search_path(conn, schema_name)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT version, description, checksum, applied_by, applied_at "
            "FROM schema_version ORDER BY version"
        )
        return cur.fetchall()


def apply_migrations(
    conn,
    schema_name: str = SCHEMA_NAME,
    applied_by: str = "bic.init",
) -> list[int]:
    """Apply pending migrations in version order; return newly applied versions.

    Each migration runs in its own transaction together with its ledger row.
    """
    validate_schema_name(schema_name)
    ensure_ledger(conn, schema_name)
    applied = {row[0] for row in applied_migrations(conn, schema_name)}
    newly_applied: list[int] = []
    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        with conn.cursor() as cur:
            cur.execute(migration.sql)
            cur.execute(
                "INSERT INTO schema_version "
                "(version, description, checksum, applied_by) "
                "VALUES (%s, %s, %s, %s)",
                (
                    migration.version,
                    migration.description,
                    migration.checksum,
                    applied_by,
                ),
            )
        conn.commit()
        newly_applied.append(migration.version)
    return newly_applied


def current_schema_version(conn, schema_name: str = SCHEMA_NAME) -> int:
    """Highest applied version, or 0 when the ledger does not exist yet."""
    validate_schema_name(schema_name)
    _set_search_path(conn, schema_name)
    if not _ledger_exists(conn, schema_name):
        return 0
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version")
        return int(cur.fetchone()[0])


def is_current(conn, schema_name: str = SCHEMA_NAME) -> bool:
    return current_schema_version(conn, schema_name) == latest_schema_version()


def verify_checksums(conn, schema_name: str = SCHEMA_NAME) -> list[dict]:
    """Compare ledger checksums against the frozen migration definitions.

    Returns [] when the ledger does not exist yet.
    """
    validate_schema_name(schema_name)
    if not _ledger_exists(conn, schema_name):
        return []
    by_version = {migration.version: migration for migration in MIGRATIONS}
    results: list[dict] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT version, checksum FROM schema_version ORDER BY version"
        )
        for version, stored in cur.fetchall():
            expected = by_version.get(version)
            if expected is None:
                results.append(
                    {
                        "version": version,
                        "ok": False,
                        "stored": stored,
                        "expected": None,
                        "note": "unknown version in ledger",
                    }
                )
            else:
                results.append(
                    {
                        "version": version,
                        "ok": stored == expected.checksum,
                        "stored": stored,
                        "expected": expected.checksum,
                    }
                )
    return results
