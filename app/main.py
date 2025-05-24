import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.db.session import get_db
from app.integrations.external_database import external_db
from app.utils.logging import get_logger
from app.utils.llm import bedrock_client
from app.services.job_service import job_service

logger = get_logger("main")

# Define lifespan using asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for the application"""
    try:
        # Initialize database (startup)
        async for db in get_db():
            await init_db(db)
            break
        
        # Initialize job service
        logger.info("Initializing job service...")
        # job_service will initialize its Redis connection on first use
        
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    
    yield  # This is where the application runs
    
    try:
        # Cleanup resources (shutdown)
        logger.info("Shutting down application...")
        
        # Close external database connection
        await external_db.close()
        
        # Close Bedrock client
        await bedrock_client.close()
        
        # Close job service
        await job_service.close()
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

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

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static files from {static_dir}")
else:
    logger.warning(f"Static directory {static_dir} does not exist, skipping mount")

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

# Job status endpoint
@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        logger.info("getting status")
        status = await job_service.get_job_status(job_id)
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting job status")

# Queue info endpoint
@app.get("/queue-info")
async def get_queue_info():
    """Get queue information"""
    try:
        return await job_service.get_queue_info()
    except Exception as e:
        logger.error(f"Error getting queue info: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting queue info")

# Serve index.html for root path
@app.get("/")
async def get_index():
    """Serve the index.html file"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        logger.error(f"Index file {index_path} does not exist")
        raise HTTPException(status_code=404, detail="Index file not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)