#!/usr/bin/env python
"""
CLI utility for importing/exporting the project_data.db database.

Features:
  - Export to JSON (default) or CSV
  - Import from JSON or CSV into a target database
  - Modes: replace (drop & recreate table), append, merge (upsert on Project Part name)
  - Automatic timestamped backup before destructive operations (replace/merge) unless --no-backup
  - Optional --database path override (defaults to project_data.db in current directory)

Examples:
  python cli.py export --out data.json
  python cli.py export --format csv --out parts.csv
  python cli.py import --in data.json --mode merge
  python cli.py import --in parts.csv --format csv --mode replace --database other.db

Exit Codes:
  0 success
  2 invalid arguments
  3 IO error
  4 database error
"""
import argparse, sys, json, csv, os, sqlite3, shutil, datetime as dt

DB_FILE_DEFAULT = "project_data.db"
TABLE_NAME = "project_parts"

# Columns aligned with model (must match order in existing table)
COLUMNS = [
    "Project Part","Parent","Children","Start Date","Duration (days)",
    "Internal/External","Dependencies","Type","Calculated End Date","Resources",
    "Notes","Responsible","Images","Pace Link","Attachments","% Complete","Status",
    "Actual Start Date","Actual Finish Date","Baseline Start Date","Baseline End Date"
]

PRIMARY_KEY = "Project Part"  # logical unique identifier

class CLIError(Exception):
    pass

def connect(db_path):
    try:
        return sqlite3.connect(db_path)
    except Exception as e:
        raise CLIError(f"Could not open database {db_path}: {e}")

def ensure_table(conn):
    # We assume table exists; minimal fallback create if missing.
    cols = [f"[{c}] TEXT" for c in COLUMNS]
    sql = f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (id INTEGER PRIMARY KEY AUTOINCREMENT, " \
          + ",".join(cols) + ")"
    conn.execute(sql)
    conn.commit()

def backup(db_path):
    if not os.path.exists(db_path):
        return None
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.bak_{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path

def export_data(db_path, out_path, fmt):
    conn = connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {','.join('['+c+']' for c in COLUMNS)} FROM {TABLE_NAME}")
        rows = [dict(zip(COLUMNS, r)) for r in cur.fetchall()]
    except Exception as e:
        raise CLIError(f"Failed reading data: {e}")
    finally:
        conn.close()
    try:
        if fmt == 'json':
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
        elif fmt == 'csv':
            with open(out_path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                w.writeheader()
                for r in rows:
                    w.writerow(r)
        else:
            raise CLIError(f"Unsupported export format: {fmt}")
    except Exception as e:
        raise CLIError(f"Failed writing output {out_path}: {e}")
    return len(rows)

def read_input(in_path, fmt):
    if not os.path.exists(in_path):
        raise CLIError(f"Input file not found: {in_path}")
    try:
        if fmt == 'json':
            with open(in_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise CLIError("JSON root must be an array of objects")
        elif fmt == 'csv':
            with open(in_path, 'r', encoding='utf-8') as f:
                r = csv.DictReader(f)
                data = [dict(row) for row in r]
        else:
            raise CLIError(f"Unsupported import format: {fmt}")
    except CLIError:
        raise
    except Exception as e:
        raise CLIError(f"Failed reading input: {e}")
    # Normalize columns: ensure all defined keys
    norm = []
    for row in data:
        new_row = {c: (row.get(c) or "") for c in COLUMNS}
        norm.append(new_row)
    return norm

def import_data(db_path, in_path, fmt, mode, do_backup=True):
    rows = read_input(in_path, fmt)
    conn = connect(db_path)
    ensure_table(conn)
    if mode not in ("append","replace","merge"):
        raise CLIError(f"Invalid mode: {mode}")
    backup_path = None
    try:
        if mode in ("replace","merge") and do_backup:
            backup_path = backup(db_path)
        cur = conn.cursor()
        if mode == 'replace':
            # simplest: delete all existing logical rows (keep schema)
            cur.execute(f"DELETE FROM {TABLE_NAME}")
        elif mode == 'merge':
            # build index of existing
            cur.execute(f"SELECT [{PRIMARY_KEY}] FROM {TABLE_NAME}")
            existing = {r[0] for r in cur.fetchall() if r and r[0] is not None}
        # Insert / upsert
        inserted = 0; updated = 0
        for r in rows:
            pk = r.get(PRIMARY_KEY, "").strip()
            vals = [r.get(c, "") for c in COLUMNS]
            placeholders = ",".join(['?']*len(COLUMNS))
            if mode == 'append':
                cur.execute(f"INSERT INTO {TABLE_NAME} ({','.join('['+c+']' for c in COLUMNS)}) VALUES ({placeholders})", vals)
                inserted += 1
            elif mode == 'replace':
                cur.execute(f"INSERT INTO {TABLE_NAME} ({','.join('['+c+']' for c in COLUMNS)}) VALUES ({placeholders})", vals)
                inserted += 1
            elif mode == 'merge':
                if pk and pk in existing:
                    # update
                    set_clause = ",".join(f"[{c}]=?" for c in COLUMNS)
                    cur.execute(f"UPDATE {TABLE_NAME} SET {set_clause} WHERE [{PRIMARY_KEY}]=?", vals + [pk])
                    updated += 1
                else:
                    cur.execute(f"INSERT INTO {TABLE_NAME} ({','.join('['+c+']' for c in COLUMNS)}) VALUES ({placeholders})", vals)
                    inserted += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise CLIError(f"Import failed: {e}")
    finally:
        conn.close()
    return {
        'rows_in_file': len(rows),
        'inserted': inserted,
        'updated': updated,
        'backup': backup_path
    }

def parse_args(argv):
    p = argparse.ArgumentParser(description="Import/export utility for project_data.db")
    sub = p.add_subparsers(dest='command', required=True)

    exp = sub.add_parser('export', help='Export database to file')
    exp.add_argument('--database', default=DB_FILE_DEFAULT, help='Path to SQLite DB (default: project_data.db)')
    exp.add_argument('--out', required=True, help='Output file path')
    exp.add_argument('--format', choices=['json','csv'], default='json', help='Export format (default json)')

    imp = sub.add_parser('import', help='Import file into database')
    imp.add_argument('--database', default=DB_FILE_DEFAULT, help='Path to SQLite DB (default: project_data.db)')
    imp.add_argument('--in', dest='in_file', required=True, help='Input file path')
    imp.add_argument('--format', choices=['json','csv'], help='Input format (infer from extension if omitted)')
    imp.add_argument('--mode', choices=['append','replace','merge'], default='merge', help='How to apply records (default merge)')
    imp.add_argument('--no-backup', action='store_true', help='Skip automatic backup before replace/merge')

    return p.parse_args(argv)

def infer_format(path, override):
    if override:
        return override
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json': return 'json'
    if ext == '.csv': return 'csv'
    raise CLIError("Cannot infer format from extension; specify --format")

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        args = parse_args(argv)
        if args.command == 'export':
            count = export_data(args.database, args.out, args.format)
            print(f"Exported {count} rows to {args.out}")
            return 0
        elif args.command == 'import':
            fmt = infer_format(args.in_file, args.format)
            result = import_data(args.database, args.in_file, fmt, args.mode, do_backup=not args.no_backup)
            msg = (f"Import complete: file_rows={result['rows_in_file']} inserted={result['inserted']} updated={result['updated']}")
            if result['backup']:
                msg += f" backup={result['backup']}"
            print(msg)
            return 0
        else:
            return 2
    except CLIError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        return 4

if __name__ == '__main__':
    sys.exit(main())
