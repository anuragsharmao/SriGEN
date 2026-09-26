"""SriGEN Main Application Entrypoint."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.core.config import settings
from app.db.database import SessionLocal, init_db
from app.services.auth import bootstrap_default_operator

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("srigen.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database tables on startup."""
    logger.info("Initializing SriGEN database tables...")
    init_db()
    db = SessionLocal()
    try:
        bootstrap_default_operator(db)
    finally:
        db.close()
    logger.info("SriGEN database initialized successfully.")
    yield
    logger.info("Shutting down SriGEN service.")


app = FastAPI(
    title="SriGEN Backend API",
    description=(
        "Secure Generative AI Platform for Multi-Format Content Transformation & Verification "
        "(NTRO | SIH 2026). Implements UNDERSTAND -> CONTROL -> GENERATE -> VERIFY -> REVIEW -> PROVE."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration for frontend integrations. Explicit allowlist
# only (settings.CORS_ORIGINS strips any "*" automatically) — never combine a
# wildcard with allow_credentials=True, which is always True here since every
# authenticated request carries a bearer token.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routes under /api
app.include_router(api_router)


@app.get("/", tags=["System"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs",
        "architecture_stages": [
            "UNDERSTAND (Ingestion + Canonical Fact Graph)",
            "CONTROL (Sensitivity Firewall + Content Intelligence Resolver)",
            "GENERATE (Multi-Select Adapter Parallel Fan-Out)",
            "VERIFY (Grounding Guard + Cross-Output Consistency)",
            "REVIEW (Operator Dashboard + Evidence View)",
            "PROVE (Provenance Ledger Local Hash-Chain)"
        ]
    }


@app.get("/health", tags=["System"])
async def health_check():
    from app.core.llm_client import llm_client
    llm_reachable = await llm_client.check_reachable()
    return {
        "status": "healthy" if llm_reachable else "degraded",
        "database": "connected",
        "groq_configured": bool(settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_your_")),
        "llm_reachable": llm_reachable,
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
