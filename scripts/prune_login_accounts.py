"""
Keep only selected login accounts in local SQLite DB.

Usage:
  python scripts/prune_login_accounts.py --dry-run
  python scripts/prune_login_accounts.py --apply
  python scripts/prune_login_accounts.py --apply --keep srinath hari
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


def _all_tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [row[0] for row in rows]


def _get_user_fk_columns(con: sqlite3.Connection, table_name: str) -> list[str]:
    cols: list[str] = []
    for fk in con.execute(f'PRAGMA foreign_key_list("{table_name}")').fetchall():
        # fk tuple: (id, seq, table, from, to, on_update, on_delete, match)
        if fk[2] == "users":
            cols.append(fk[3])
    # unique preserve order
    seen: set[str] = set()
    ordered = []
    for col in cols:
        if col not in seen:
            seen.add(col)
            ordered.append(col)
    return ordered


def _backup_database(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_suffix(f".accounts_backup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def _normalize(s: str | None) -> str:
    return (s or "").strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune login accounts and keep selected users")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="Path to SQLite DB")
    parser.add_argument("--keep", nargs="+", default=["srinath", "hari"], help="Usernames/names to keep")
    parser.add_argument("--dry-run", action="store_true", help="Show plan only")
    parser.add_argument("--apply", action="store_true", help="Apply deletion")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        print("Use only one of --dry-run or --apply.")
        return 2
    if not args.dry_run and not args.apply:
        print("No action selected. Use --dry-run or --apply.")
        return 2

    keep_set = {_normalize(v) for v in args.keep}
    db_path = Path(args.db_path).resolve()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        users = con.execute("SELECT id, username, name, email FROM users ORDER BY id").fetchall()
        keep_rows = [
            r for r in users
            if _normalize(r["username"]) in keep_set or _normalize(r["name"]) in keep_set
        ]
        delete_rows = [r for r in users if r not in keep_rows]
        delete_ids = [int(r["id"]) for r in delete_rows]

        print(f"Database: {db_path}")
        print(f"Keep set: {sorted(keep_set)}")
        print("\nUsers to keep:")
        for r in keep_rows:
            print(f"  - id={r['id']} username={r['username']} name={r['name']}")

        print("\nUsers to delete:")
        if delete_rows:
            for r in delete_rows:
                print(f"  - id={r['id']} username={r['username']} name={r['name']}")
        else:
            print("  - none")

        if not keep_rows:
            print("\nNo matching keep users found. Aborting.")
            return 1

        if args.dry_run:
            print("\nDry run complete. No changes applied.")
            return 0

        if not delete_ids:
            print("\nNothing to delete.")
            return 0

        backup_path = _backup_database(db_path)
        print(f"\nBackup created: {backup_path}")

        table_cleanup: list[tuple[str, str]] = []
        for table_name in _all_tables(con):
            if table_name == "users":
                continue
            for col in _get_user_fk_columns(con, table_name):
                table_cleanup.append((table_name, col))

        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN")
        try:
            affected = 0
            if delete_ids:
                placeholders = ",".join(["?"] * len(delete_ids))
                for table_name, col in table_cleanup:
                    sql = f'DELETE FROM "{table_name}" WHERE "{col}" IN ({placeholders})'
                    cur = con.execute(sql, delete_ids)
                    affected += cur.rowcount if cur.rowcount != -1 else 0

                cur = con.execute(f'DELETE FROM users WHERE id IN ({placeholders})', delete_ids)
                affected += cur.rowcount if cur.rowcount != -1 else 0

            con.execute("COMMIT")
            print(f"\nRows deleted/cleaned (reported): {affected}")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.execute("PRAGMA foreign_keys=ON")

        remain_users = con.execute(
            "SELECT id, username, name FROM users ORDER BY id"
        ).fetchall()

        print("\nRemaining users:")
        for r in remain_users:
            print(f"  - id={r['id']} username={r['username']} name={r['name']}")

        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
