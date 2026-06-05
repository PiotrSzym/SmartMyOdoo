import sqlite3

conn = sqlite3.connect("smartmyodoo.db")
cursor = conn.cursor()
for table in ["proposals", "token_usage", "audit_log"]:
    try:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN workspace_id VARCHAR DEFAULT 'default'"
        )
        print(f"{table} altered")
    except Exception as e:
        print(f"Error on {table}: {e}")

conn.commit()
conn.close()
