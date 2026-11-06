"""RePersona FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.middleware import RateLimitMiddleware
from app.routers import chat, conversations, health, jobs, personas, providers, uploads

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("repersona")

ETHICAL_NOTICE = (
    "RePersona generates an AI simulation based on publicly available and "
    "processed historical material. It does not represent the consciousness, "
    "identity, or literal communication of the original person."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.demo_mode:
        # Seed a ready Osho demo persona so /explore has content immediately.
        try:
            from app.services.demo_builder import build_ready_persona

            db = SessionLocal()
            try:
                build_ready_persona(db, "Osho", force_demo=True)
                logger.info("Demo persona 'Osho' ready.")
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Demo seed skipped: %s", exc)
    yield


app = FastAPI(
    title="RePersona API",
    version="0.1.0",
    description="AI-Powered Personality Reconstruction from Multimodal Historical Data.",
    lifespan=lifespan,
)

# Rate limit added first so CORS (added last) stays outermost and its headers
# are present on 429 responses too.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"
app.include_router(health.router, prefix=api_prefix)
app.include_router(providers.router, prefix=api_prefix)
app.include_router(personas.router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)
app.include_router(jobs.router, prefix=api_prefix)
app.include_router(chat.router, prefix=api_prefix)
app.include_router(conversations.router, prefix=api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "tagline": "Explore the documented mind of history.",
        "docs": "/docs",
        "ethical_notice": ETHICAL_NOTICE,
    }


@app.get(f"{api_prefix}/ethical-notice")
def ethical_notice() -> dict:
    return {"notice": ETHICAL_NOTICE}
