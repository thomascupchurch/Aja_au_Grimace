import argparse
import sqlite3
from sqlalchemy import create_engine, text
import sys

def main(sqlite_path, pg_url):
    # Connect to SQLite
    con = sqlite3.connect(sqlite_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM project_parts")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    print(f"Fetched {len(rows)} rows from SQLite.")

    # Connect to Postgres
    engine = create_engine(pg_url)
    with engine.connect() as conn:
        # Create table if not exists (simple schema, adjust types as needed)
        col_defs = ', '.join([f'"{col}" TEXT' for col in columns])
        conn.execute(text(f'CREATE TABLE IF NOT EXISTS project_parts ({col_defs})'))
        # Truncate table
        conn.execute(text('TRUNCATE TABLE project_parts'))
        # Insert rows using positional parameters and quoted column names
        placeholders = ', '.join([f':v{i}' for i in range(len(columns))])
        colnames = ', '.join([f'"{col}"' for col in columns])
        sql = text(f'INSERT INTO project_parts ({colnames}) VALUES ({placeholders})')
        for row in rows:
            params = {f'v{i}': row[i] for i in range(len(columns))}
            conn.execute(sql, params)
        print(f"Inserted {len(rows)} rows into Postgres.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate SQLite project_parts to Postgres")
    parser.add_argument("--sqlite", required=True, help="Path to SQLite DB")
    parser.add_argument("--postgres", required=True, help="Postgres connection string")
    args = parser.parse_args()
    try:
        main(args.sqlite, args.postgres)
    except Exception as e:
        print("Migration failed:", e)
        sys.exit(1)