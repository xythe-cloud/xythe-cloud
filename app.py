"""
Xythe Cloud - Main Application
Entry point for the FastAPI server.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database.connection import init_db, check_db_connection
from src.api.auth import router as auth_router
from src.api.upload import router as upload_router
from src.api.payments import router as payments_router
from src.api.webhooks import router as webhooks_router
from src.api.workspace import router as workspace_router
from src.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Create database tables
    init_db()

    # Check database connection
    db_ok = check_db_connection()
    if db_ok:
        logger.info("Database connected")
    else:
        logger.error("Database connection failed!")

    yield

    # Shutdown
    logger.info("Shutting down Xythe Cloud")


# Create the FastAPI app
app = FastAPI(
    title="Xythe Cloud",
    description="Private AI Assistant - Cloud Backend",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhooks_router)
app.include_router(workspace_router)
app.include_router(upload_router)
app.include_router(auth_router)
app.include_router(payments_router)


# Health check endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    db_ok = await check_db_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected"
    }


# Run directly for development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="192.168.8.3", port=8000, reload=True)