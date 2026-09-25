from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_setting, DATA_DIR


class Base(DeclarativeBase):
    pass


def get_engine():
    db_path = get_setting("db_path", str(DATA_DIR / "careerkit.db"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from ..models import profile, job, cv, scanner, reachout  # noqa: F401 — registers models
    Base.metadata.create_all(bind=engine)
    # Add columns that may not exist in databases created before migrations
    _migrations = [
        ("job_applications", "tailored_cv", "TEXT"),
        ("work_experience", "employer_public_name", "VARCHAR(200)"),
        ("work_experience", "alternative_titles", "TEXT DEFAULT '[]'"),
        ("work_experience", "confidentiality_level", "VARCHAR(20) DEFAULT 'cv_safe'"),
        ("skills", "aliases", "TEXT DEFAULT '[]'"),
        ("skills", "last_used", "VARCHAR(20)"),
        ("skills", "production_experience", "BOOLEAN DEFAULT 1"),
        ("achievements", "confidentiality_level", "VARCHAR(20) DEFAULT 'cv_safe'"),
        ("projects", "confidentiality_level", "VARCHAR(20) DEFAULT 'cv_safe'"),
        ("evidence_items", "confidentiality_level", "VARCHAR(20) DEFAULT 'cv_safe'"),
        ("certifications", "status", "VARCHAR(30) DEFAULT 'active'"),
        ("certifications", "notes", "TEXT"),
    ]
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, col_type in _migrations:
            existing_columns = {item["name"] for item in inspector.get_columns(table)}
            if column not in existing_columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
