from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.db.database import Base, engine, ensure_detection_schema

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

Base.metadata.create_all(bind=engine)
ensure_detection_schema()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(router)
