#!/usr/bin/env python3
"""
Migrate (or sync) the project_parts table from a local SQLite database
into a MySQL database (such as PythonAnywhere MySQL) using SQLAlchemy.

Usage examples:
  python web/migrate_sqlite_to_mysql.py --sqlite ./project_data.db \
      --mysql "mysql+pymysql://user:pass@host/user$db?charset=utf8mb4" \
      --create --replace

Options:
  --sqlite <path>   Path to source SQLite DB file (defaults to PROJECT_DB_PATH or ./project_data.db)
  --mysql <url>     SQLAlchemy URL for MySQL (or other) database; if omitted, uses WEB_DB_URL
  --table <name>    Table name to migrate (default: project_parts)
  --create          Create table if it does not exist (quoted identifiers)
  --replace         Drop table first (destructive) before creating
  --truncate        TRUNCATE the table before inserting (if exists)
  --batch-size N    Insert in batches (default: 1000)

Notes:
- Column names are copied as-is (including spaces/parentheses). SQLAlchemy will
  handle quoting when creating/inserting.
- All data are treated as strings/ints/floats where possible; complex types are
  left as-is and may require manual cleanup if MySQL rejects them.
"""
import argparse
import os
import sqlite3
from typing import List, Dict

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def read_sqlite_rows(sqlite_path: str, table: str) -> List[Dict]:
    con = sqlite3.connect(sqlite_path)
    try:
        cur = con.cursor()
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        out = []
        for row in rows:
            rec = {k: v for k, v in zip(cols, row)}
            out.append(rec)
        return out
    finally:
        con.close()


def qi(identifier: str) -> str:
    """Quote an identifier for MySQL and escape percent signs for DBAPI string interpolation.

    - Wrap with backticks to preserve spaces/symbols.
    - Escape any literal `%` as `%%` to avoid PyMySQL treating them as placeholders.
    """
    # Backticks inside names are extremely unlikely; if present, double them
    safe = identifier.replace("`", "``").replace("%", "%%")
    return f"`{safe}`"


def ensure_table(engine, table: str, sample: Dict, drop_first: bool, create_if_missing: bool):
    # Construct a CREATE TABLE with quoted identifiers based on sample row
    # Use LONGTEXT for text-ish data, DOUBLE for floats, BIGINT for ints when possible
    # Keep it simple and safe; this is not a strict schema inference
    def col_type(v):
        if isinstance(v, (int,)):
            return "BIGINT"
        if isinstance(v, (float,)):
            return "DOUBLE"
        # default to text; dates stored as text are fine for the web viewer
        return "LONGTEXT"

    with engine.begin() as conn:
        if drop_first:
            conn.execute(text(f"DROP TABLE IF EXISTS {qi(table)}"))
        # Check existence
        exists = False
        try:
            conn.execute(text(f"SELECT 1 FROM {qi(table)} LIMIT 1"))
            exists = True
        except Exception:
            exists = False
        if exists and not create_if_missing:
            return
        if not exists and not create_if_missing:
            return
        if not exists:
            cols_sql = []
            for k, v in sample.items():
                cols_sql.append(f"{qi(k)} {col_type(v)}")
            ddl = f"CREATE TABLE {qi(table)} (" + ", ".join(cols_sql) + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            conn.execute(text(ddl))


def migrate(sqlite_path: str, mysql_url: str, table: str, create: bool, replace: bool, truncate: bool, batch_size: int):
    rows = read_sqlite_rows(sqlite_path, table)
    if not rows:
        print(f"[migrate] No rows found in {sqlite_path}:{table}")
        return

    engine = create_engine(mysql_url, pool_pre_ping=True)
    ensure_table(engine, table, rows[0], drop_first=replace, create_if_missing=create)

    # Use driver-level positional params to avoid issues with special column names
    # Build INSERT with %s placeholders and execute via the DBAPI driver
    keys = list(rows[0].keys())
    col_list = ",".join([qi(k) for k in keys])
    insert_sql = f"INSERT INTO {qi(table)} ({col_list}) VALUES (" + ",".join(["%s"] * len(keys)) + ")"

    # Prepare batch values in column order; coerce empty strings to None to be safe
    def to_tuple(rec: Dict) -> tuple:
        out = []
        for k in keys:
            v = rec.get(k)
            if v == "":
                v = None
            out.append(v)
        return tuple(out)

    raw_conn = engine.raw_connection()
    cur = None
    try:
        cur = raw_conn.cursor()
        if truncate and not replace:
            cur.execute(f"TRUNCATE TABLE {qi(table)}")
        batch_vals = []
        count = 0
        for rec in rows:
            batch_vals.append(to_tuple(rec))
            if len(batch_vals) >= batch_size:
                cur.executemany(insert_sql, batch_vals)
                count += len(batch_vals)
                batch_vals.clear()
        if batch_vals:
            cur.executemany(insert_sql, batch_vals)
            count += len(batch_vals)
        raw_conn.commit()
        print(f"[migrate] Inserted {count} rows into `{table}`")
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        try:
            raw_conn.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default=os.environ.get("PROJECT_DB_PATH", "./project_data.db"))
    ap.add_argument("--mysql", default=os.environ.get("WEB_DB_URL", ""))
    ap.add_argument("--table", default="project_parts")
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--truncate", action="store_true")
    ap.add_argument("--batch-size", type=int, default=1000)
    args = ap.parse_args()

    if not args.mysql:
        raise SystemExit("--mysql (or WEB_DB_URL) is required")
    if not os.path.isfile(args.sqlite):
        raise SystemExit(f"SQLite file not found: {args.sqlite}")

    try:
        migrate(args.sqlite, args.mysql, args.table, args.create, args.replace, args.truncate, args.batch_size)
    except SQLAlchemyError as e:
        raise SystemExit(f"SQLAlchemy error: {e}")


if __name__ == "__main__":
    main()
