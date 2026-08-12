"""
init_db.py
Applies database/schema.sql to an already-running Postgres instance.
Useful if the container's data volume already existed before you added
the schema (Docker only auto-runs init scripts on a *fresh* volume).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2

import config


def main():
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()

    conn = psycopg2.connect(config.get_db_dsn())
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(schema_sql)
    cur.close()
    conn.close()
    print("[init_db] Schema applied successfully.")


if __name__ == "__main__":
    main()
