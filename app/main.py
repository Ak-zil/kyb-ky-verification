import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.integrations.external_database import external_db

# Define lifespan using asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the application"""
    try:
        # Initialize database (startup)
        async for db in get_db():
            await init_db(db)
            break
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        raise
    
    yield  # This is where the application runs
    
    try:
        # Cleanup resources (shutdown)
        await external_db.close()
    except Exception as e:
        logging.error(f"Error closing external database connection: {str(e)}")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Configure CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)