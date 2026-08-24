"""FastAPI application entry point for the Smart Resume Screener."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.database import init_db
from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB on startup."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Log LLM provider status
    from services.llm_client import get_llm_client
    client = get_llm_client()
    status = client.get_provider_status()
    logger.info(f"LLM providers: {status}")
    if not client.is_available:
        logger.warning(
            "No LLM API keys configured! Set GEMINI_API_KEY or GROQ_API_KEY "
            "in .env file. The system will use deterministic scoring only."
        )

    yield

    logger.info("Shutting down...")


# Create the FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Intelligent resume screening and candidate ranking system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],  # permissive for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint — basic info."""
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
