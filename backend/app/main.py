from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import RequestContextMiddleware, configure_logging
from app.db.base import Base, SessionLocal, engine
from app.db.migrations import run_migrations
from app.services.analysis import seed_demo_dataset

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations(engine)
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo_data:
        db = SessionLocal()
        try:
            seed_demo_dataset(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    description="Plataforma de analise inteligente para trade com foco em risco, dados e decisao realista.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

app.include_router(router, prefix=settings.api_v1_prefix)
