"""Reset the database: drop all tables, recreate schema, reimport master workbook."""
import psycopg2
from app.config import DATABASE_URL, MASTER_XLSX
from app.db import SCHEMA_SQL, import_master_workbook

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

print("Dropping all tables...")
cur.execute("DROP TABLE IF EXISTS audit_events CASCADE")
cur.execute("DROP TABLE IF EXISTS system_versions CASCADE")
cur.execute("DROP TABLE IF EXISTS candidates CASCADE")
cur.execute("DROP TABLE IF EXISTS submissions CASCADE")
cur.execute("DROP TABLE IF EXISTS systems CASCADE")

print("Recreating schema...")
cur.execute(SCHEMA_SQL)
conn.close()

print(f"Importing master workbook: {MASTER_XLSX.name}")
count = import_master_workbook(MASTER_XLSX)
print(f"Imported {count} systems.")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM systems")
print(f"Total systems in database: {cur.fetchone()[0]}")
conn.close()
