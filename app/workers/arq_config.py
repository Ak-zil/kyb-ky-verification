import logging
from typing import Any, Dict, Optional

from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

from app.core.config import settings
from app.utils.logging import get_logger

from app.workers.verification_worker import run_agent_verification, run_business_verification, run_kyc_verification

logger = get_logger("arq_config")


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for Arq"""
    redis_settings  =  RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        database=settings.REDIS_DB
    )

    return redis_settings


async def startup(ctx: Worker) -> None:
    """Startup function for Arq worker"""
    logger.info("Starting Arq worker...")
    
    # Initialize any resources needed by workers
    # For example, database connections, external clients, etc.
    ctx['logger'] = logger


async def shutdown(ctx: Worker) -> None:
    """Shutdown function for Arq worker"""
    logger.info("Shutting down Arq worker...")
    
    # Clean up resources
    pass


class WorkerSettings:
    """Arq worker settings"""
    
    functions = [
        # Import worker functions here
        # 'app.workers.verification_worker.run_kyc_verification',
        # 'app.workers.verification_worker.run_business_verification',
        # 'app.workers.verification_worker.run_agent_verification',
        run_agent_verification, 
        run_business_verification, 
        run_kyc_verification
    ]
    
    redis_settings = get_redis_settings()
    
    # Worker configuration
    queue_name = settings.ARQ_QUEUE_NAME
    max_jobs = settings.ARQ_MAX_WORKERS
    job_timeout = settings.ARQ_JOB_TIMEOUT
    keep_result = settings.ARQ_KEEP_RESULT
    
    # Startup/shutdown hooks
    on_startup = startup
    on_shutdown = shutdown
    
    # Logging
    log_results = True
    
    # Health check
    health_check_interval = 30


async def get_redis_pool():
    """Get Redis connection pool"""
    return await create_pool(get_redis_settings(), default_queue_name= settings.ARQ_QUEUE_NAME)