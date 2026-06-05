from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_detection_schema() -> None:
    columns = {
        "vehicle_crop_blob": "BLOB",
        "plate_crop_blob": "BLOB",
        "vehicle_bbox": "VARCHAR(100)",
        "plate_bbox": "VARCHAR(100)",
        "report_json": "TEXT",
        "reason": "VARCHAR(50)",
    }

    with engine.begin() as connection:
        existing = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(detections)").fetchall()
        }
        for name, column_type in columns.items():
            if name not in existing:
                connection.exec_driver_sql(
                    f"ALTER TABLE detections ADD COLUMN {name} {column_type}"
                )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
