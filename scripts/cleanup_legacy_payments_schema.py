"""
One-time legacy payments schema cleanup for local SQLite databases.

This script physically removes deprecated payment/subscription tables and
obsolete user columns that are no longer present in ORM models.

Usage:
    python scripts/cleanup_legacy_payments_schema.py --dry-run
    python scripts/cleanup_legacy_payments_schema.py --apply

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

LEGACY_TABLES = [
    "payment_retry_queue",
    "wallet_transactions",
    "user_wallet",
    "promo_redemptions",
    "referrals",
    "invoices",
    "payments",
    "user_subscriptions",
    "promo_codes",
    "subscription_plans",
]

LEGACY_USER_COLUMNS = [
    "subscription_status",
    "subscription_expires_at",
    "lifetime_value_inr",
    "referral_code",
]


def _existing_tables(con: sqlite3.Connection) -> set[str]:
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def _existing_user_columns(con: sqlite3.Connection) -> list[str]:
    rows = con.execute("PRAGMA table_info(users)").fetchall()
    return [row[1] for row in rows]


def _user_indexes_for_column(con: sqlite3.Connection, column_name: str) -> list[str]:
    indexes: list[str] = []
    for row in con.execute("PRAGMA index_list(users)").fetchall():
        index_name = row[1]
        index_cols = [c[2] for c in con.execute(f"PRAGMA index_info({index_name})").fetchall()]
        if column_name in index_cols:
            indexes.append(index_name)
    return indexes


def _print_plan(con: sqlite3.Connection) -> tuple[list[str], list[str], list[str]]:
    tables = _existing_tables(con)
    user_columns = _existing_user_columns(con)

    tables_to_drop = [name for name in LEGACY_TABLES if name in tables]
    columns_to_drop = [name for name in LEGACY_USER_COLUMNS if name in user_columns]

    indexes_to_drop: list[str] = []
    for col in columns_to_drop:
        indexes_to_drop.extend(_user_indexes_for_column(con, col))
    indexes_to_drop = sorted(set(indexes_to_drop))

    print("Legacy payment tables found:")
    if tables_to_drop:
        for name in tables_to_drop:
            print(f"  - {name}")
    else:
        print("  - none")

    print("Legacy users columns found:")
    if columns_to_drop:
        for name in columns_to_drop:
            print(f"  - {name}")
    else:
        print("  - none")

    print("Dependent users indexes to drop:")
    if indexes_to_drop:
        for name in indexes_to_drop:
            print(f"  - {name}")
    else:
        print("  - none")

    return tables_to_drop, columns_to_drop, indexes_to_drop


def _backup_database(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".backup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def _apply_cleanup(con: sqlite3.Connection, tables: list[str], columns: list[str], indexes: list[str]) -> None:
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("BEGIN")
    try:
        for index_name in indexes:
            con.execute(f"DROP INDEX IF EXISTS {index_name}")

        for table_name in tables:
            con.execute(f"DROP TABLE IF EXISTS {table_name}")

        for column_name in columns:
            con.execute(f"ALTER TABLE users DROP COLUMN {column_name}")

        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.execute("PRAGMA foreign_keys=ON")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup legacy payments schema from SQLite DB")
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

        tables_to_drop, columns_to_drop, indexes_to_drop = _print_plan(con)

        if args.dry_run:
            print("\nDry run complete. No changes applied.")
            return 0

        if not tables_to_drop and not columns_to_drop:
            print("\nNothing to clean up. Schema is already aligned.")
            return 0

        backup_path = _backup_database(db_path)
        print(f"\nBackup created: {backup_path}")

        _apply_cleanup(
            con,
            tables=tables_to_drop,
            columns=columns_to_drop,
            indexes=indexes_to_drop,
        )

        print("\nCleanup applied. Verifying...")
        remaining_tables, remaining_columns, remaining_indexes = _print_plan(con)

        if remaining_tables or remaining_columns:
            print("\nVerification failed: legacy schema elements still present.")
            return 1

        if remaining_indexes:
            print("\nWarning: indexes still detected for removed columns.")
            return 1

        print("\nSuccess: legacy payments schema removed.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
