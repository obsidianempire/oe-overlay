import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth
from .config import get_settings
from .database import Base, engine
from .routers import alerts, crafting, data, events

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oe-overlay-service")

app = FastAPI(
    title="Obsidian Empire Overlay Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured.")


@app.get("/healthz", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_base_path)
app.include_router(data.router, prefix=settings.api_base_path)
app.include_router(events.router, prefix=settings.api_base_path)
app.include_router(crafting.router, prefix=settings.api_base_path)
app.include_router(alerts.router, prefix=settings.api_base_path)
