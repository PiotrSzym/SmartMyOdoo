import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///smartmyodoo.db").strip()

engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DB_PATH.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # FIX-02 S5.2: pisarze czekają (do 5s) zamiast zwracać "database is locked"
        # — odporność przy współbieżnych zapisach (np. równoległe approve pod lockiem).
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def backup_before_migrate():
    import shutil
    import time
    from pathlib import Path

    if not DB_PATH.startswith("sqlite:///"):
        return

    db_file = Path(DB_PATH.replace("sqlite:///", ""))
    if not db_file.exists():
        return

    timestamp = int(time.time() * 1000)
    backup_file = db_file.with_name(f"{db_file.name}.bak.{timestamp}")
    shutil.copy2(db_file, backup_file)

    # Retencja: zachowaj tylko 3 najnowsze
    backups = sorted(
        db_file.parent.glob(f"{db_file.name}.bak.*"), key=os.path.getmtime, reverse=True
    )
    for old_backup in backups[3:]:
        try:
            old_backup.unlink()
        except OSError:
            pass
