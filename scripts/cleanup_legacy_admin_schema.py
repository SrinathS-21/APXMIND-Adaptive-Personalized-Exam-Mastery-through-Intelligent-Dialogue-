"""
One-time legacy admin schema cleanup for local SQLite databases.

This script removes deprecated admin-only tables and rewrites remaining
support/moderation tables to drop foreign keys to removed admin tables.

Usage:
    python scripts/cleanup_legacy_admin_schema.py --dry-run
    python scripts/cleanup_legacy_admin_schema.py --apply

Notes:
- SQLite only.
- Creates a timestamped backup before applying changes.
- Safe to re-run; operations are idempotent.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "APXMIND.db"

LEGACY_REF_TABLES = {"admin_users", "admin_roles"}
DROP_ADMIN_TABLES = [
    "admin_sessions",
    "admin_actions",
    "admin_users",
    "admin_roles",
]

# Desired schema mirrors current ORM (admin FKs replaced with nullable INTEGER ids).
REWRITE_TABLES_SQL: dict[str, dict[str, object]] = {
    "support_tickets": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number VARCHAR(20) UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id),
                email VARCHAR(120) NOT NULL,
                name VARCHAR(100),
                phone VARCHAR(20),
                subject VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                subcategory VARCHAR(50),
                priority VARCHAR(20) DEFAULT 'normal',
                status VARCHAR(20) DEFAULT 'open',
                assigned_to INTEGER,
                assigned_at DATETIME,
                escalated_to INTEGER,
                escalated_at DATETIME,
                first_response_at DATETIME,
                first_response_sla_met BOOLEAN,
                resolution_sla_hours INTEGER DEFAULT 24,
                resolution_sla_met BOOLEAN,
                resolution_summary TEXT,
                resolution_type VARCHAR(30),
                resolved_at DATETIME,
                resolved_by INTEGER,
                satisfaction_rating INTEGER,
                satisfaction_comment TEXT,
                source VARCHAR(30) DEFAULT 'app',
                browser VARCHAR(50),
                os VARCHAR(50),
                app_version VARCHAR(20),
                attachments JSON,
                tags JSON,
                created_at DATETIME,
                updated_at DATETIME,
                closed_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ticket_number ON \"{table}\" (ticket_number)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_user ON \"{table}\" (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_status ON \"{table}\" (status, priority, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_assigned ON \"{table}\" (assigned_to, status)",
            "CREATE INDEX IF NOT EXISTS idx_ticket_category ON \"{table}\" (category, status)",
        ],
    },
    "canned_responses": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(50),
                tags JSON,
                usage_count INTEGER DEFAULT 0,
                created_by INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME
            )
        """,
        "indexes": [],
    },
    "content_reports": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER NOT NULL REFERENCES users(id),
                content_type VARCHAR(30) NOT NULL,
                content_id VARCHAR(64) NOT NULL,
                content_preview TEXT,
                reason VARCHAR(50) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at DATETIME,
                review_notes TEXT,
                action_taken VARCHAR(50),
                action_details TEXT,
                created_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_report_status ON \"{table}\" (status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_report_content ON \"{table}\" (content_type, content_id)",
            "CREATE INDEX IF NOT EXISTS idx_report_reporter ON \"{table}\" (reporter_id)",
        ],
    },
    "user_warnings": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                warning_type VARCHAR(30) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                reason TEXT NOT NULL,
                related_content_type VARCHAR(30),
                related_content_id VARCHAR(64),
                report_id INTEGER REFERENCES content_reports(id),
                issued_by INTEGER,
                acknowledged_at DATETIME,
                expires_at DATETIME,
                created_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_warning_user ON \"{table}\" (user_id, created_at DESC)",
        ],
    },
    "user_bans": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                ban_type VARCHAR(30) NOT NULL,
                reason TEXT NOT NULL,
                feature_restricted VARCHAR(50),
                starts_at DATETIME,
                ends_at DATETIME,
                warning_count_at_ban INTEGER,
                report_id INTEGER REFERENCES content_reports(id),
                issued_by INTEGER,
                appeal_text TEXT,
                appeal_status VARCHAR(20),
                appeal_reviewed_by INTEGER,
                appeal_reviewed_at DATETIME,
                appeal_notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                lifted_at DATETIME,
                lifted_by INTEGER,
                lift_reason TEXT,
                created_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ban_user ON \"{table}\" (user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_ban_active ON \"{table}\" (is_active, ends_at)",
        ],
    },
    "feature_flags": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                description TEXT,
                is_enabled BOOLEAN DEFAULT FALSE,
                rollout_percentage INTEGER DEFAULT 0,
                rollout_strategy VARCHAR(30),
                target_user_ids JSON,
                target_segments JSON,
                exclude_user_ids JSON,
                enable_at DATETIME,
                disable_at DATETIME,
                has_variants BOOLEAN DEFAULT FALSE,
                variants JSON,
                owner VARCHAR(100),
                jira_ticket VARCHAR(50),
                updated_by INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_feature_name ON \"{table}\" (name)",
            "CREATE INDEX IF NOT EXISTS idx_feature_enabled ON \"{table}\" (is_enabled)",
        ],
    },
    "feature_flag_overrides": {
        "create": """
            CREATE TABLE "{table}" (
                feature_id INTEGER NOT NULL REFERENCES feature_flags(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_enabled BOOLEAN NOT NULL,
                variant VARCHAR(50),
                reason TEXT,
                set_by INTEGER,
                expires_at DATETIME,
                created_at DATETIME,
                PRIMARY KEY (feature_id, user_id)
            )
        """,
        "indexes": [],
    },
    "system_settings": {
        "create": """
            CREATE TABLE "{table}" (
                key VARCHAR(100) PRIMARY KEY,
                value JSON NOT NULL,
                value_type VARCHAR(20) NOT NULL,
                description TEXT,
                category VARCHAR(50) NOT NULL,
                is_sensitive BOOLEAN DEFAULT FALSE,
                updated_by INTEGER,
                updated_at DATETIME
            )
        """,
        "indexes": [],
    },
    "announcements": {
        "create": """
            CREATE TABLE "{table}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                content_type VARCHAR(20) DEFAULT 'text',
                announcement_type VARCHAR(30) NOT NULL,
                display_location VARCHAR(30),
                priority INTEGER DEFAULT 0,
                target_all BOOLEAN DEFAULT TRUE,
                target_segments JSON,
                target_platforms JSON,
                starts_at DATETIME NOT NULL,
                ends_at DATETIME,
                is_active BOOLEAN DEFAULT TRUE,
                is_dismissible BOOLEAN DEFAULT TRUE,
                view_count INTEGER DEFAULT 0,
                dismiss_count INTEGER DEFAULT 0,
                created_by INTEGER,
                created_at DATETIME
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_announcement_active ON \"{table}\" (is_active, starts_at, ends_at)",
        ],
    },
}


def _existing_tables(con: sqlite3.Connection) -> set[str]:
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _fks_to_legacy_admin(con: sqlite3.Connection, table_name: str) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for row in con.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall():
        # (id, seq, table, from, to, on_update, on_delete, match)
        parent_table = row[2]
        from_col = row[3]
        if parent_table in LEGACY_REF_TABLES:
            refs.append((from_col, parent_table))
    return refs


def _table_columns(con: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in con.execute(f'PRAGMA table_info("{table_name}")').fetchall()]


def _all_legacy_fk_references(con: sqlite3.Connection, tables: set[str]) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for table_name in sorted(tables):
        refs = _fks_to_legacy_admin(con, table_name)
        if refs:
            out[table_name] = refs
    return out


def _print_plan(con: sqlite3.Connection) -> tuple[list[str], list[str], list[str]]:
    tables = _existing_tables(con)
    legacy_refs = _all_legacy_fk_references(con, tables)

    rewrites: list[str] = []
    unsupported_refs: list[str] = []
    for table_name in sorted(legacy_refs):
        if table_name in REWRITE_TABLES_SQL:
            rewrites.append(table_name)
        elif table_name not in DROP_ADMIN_TABLES:
            unsupported_refs.append(table_name)

    drops: list[str] = []
    for table_name in DROP_ADMIN_TABLES:
        if table_name in tables:
            if table_name in {"admin_users", "admin_roles"} and unsupported_refs:
                continue
            drops.append(table_name)

    print("Legacy admin FK references found:")
    if legacy_refs:
        for table_name, refs in legacy_refs.items():
            pretty = ", ".join([f"{col}->{parent}" for col, parent in refs])
            print(f"  - {table_name}: {pretty}")
    else:
        print("  - none")

    print("Tables to rewrite (drop admin FKs):")
    if rewrites:
        for name in rewrites:
            print(f"  - {name}")
    else:
        print("  - none")

    print("Legacy admin tables to drop:")
    if drops:
        for name in drops:
            print(f"  - {name}")
    else:
        print("  - none")

    if unsupported_refs:
        print("Unsupported legacy admin FK references (manual review required):")
        for name in unsupported_refs:
            print(f"  - {name}")

    return rewrites, drops, unsupported_refs


def _backup_database(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".admin_backup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def _rebuild_table(con: sqlite3.Connection, table_name: str) -> None:
    spec = REWRITE_TABLES_SQL[table_name]
    temp_table = f"__tmp_{table_name}"

    create_sql = str(spec["create"]).format(table=temp_table)
    index_sql = [str(stmt).format(table=table_name) for stmt in spec["indexes"]]

    con.execute(f'DROP TABLE IF EXISTS "{temp_table}"')
    con.execute(create_sql)

    old_cols = set(_table_columns(con, table_name))
    new_cols = _table_columns(con, temp_table)
    common_cols = [c for c in new_cols if c in old_cols]

    if common_cols:
        cols_csv = ", ".join([f'"{c}"' for c in common_cols])
        con.execute(
            f'INSERT INTO "{temp_table}" ({cols_csv}) SELECT {cols_csv} FROM "{table_name}"'
        )

    con.execute(f'DROP TABLE "{table_name}"')
    con.execute(f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}"')

    for stmt in index_sql:
        con.execute(stmt)


def _apply_cleanup(con: sqlite3.Connection, rewrites: list[str], drops: list[str]) -> None:
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("BEGIN")
    try:
        for table_name in rewrites:
            _rebuild_table(con, table_name)

        for table_name in drops:
            con.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.execute("PRAGMA foreign_keys=ON")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup legacy admin schema from SQLite DB")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="Path to SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="Show planned operations only")
    parser.add_argument("--apply", action="store_true", help="Execute cleanup")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        print("Use only one of --dry-run or --apply.")
        return 2
    if not args.dry_run and not args.apply:
        print("No action selected. Use --dry-run or --apply.")
        return 2

    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    con = sqlite3.connect(db_path)
    try:
        sqlite_version = con.execute("SELECT sqlite_version()").fetchone()[0]
        print(f"SQLite version: {sqlite_version}")
        print(f"Database: {db_path}")

        rewrites, drops, unsupported_refs = _print_plan(con)

        if args.dry_run:
            print("\nDry run complete. No changes applied.")
            return 0

        if unsupported_refs:
            print("\nAborting apply due to unsupported legacy admin FK references.")
            print("Please extend cleanup mapping for the listed tables or clean manually first.")
            return 1

        if not rewrites and not drops:
            print("\nNothing to clean up. Schema is already aligned.")
            return 0

        backup_path = _backup_database(db_path)
        print(f"\nBackup created: {backup_path}")

        _apply_cleanup(con, rewrites=rewrites, drops=drops)

        print("\nCleanup applied. Verifying...")
        remaining_rewrites, remaining_drops, remaining_unsupported = _print_plan(con)

        if remaining_unsupported:
            print("\nVerification failed: unsupported legacy references remain.")
            return 1

        if remaining_rewrites:
            print("\nVerification failed: some tables still require rewrite.")
            return 1

        remaining_tables = _existing_tables(con)
        dropped_still_present = [name for name in drops if name in remaining_tables]
        if dropped_still_present:
            print("\nVerification failed: some legacy admin tables are still present:")
            for name in dropped_still_present:
                print(f"  - {name}")
            return 1

        print("\nSuccess: legacy admin schema removed/aligned.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
