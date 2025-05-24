from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from arq import ArqRedis
from arq.jobs import Job

from app.workers.arq_config import get_redis_pool
from app.utils.logging import get_logger

logger = get_logger("job_service")


class JobService:
    """Service for managing Arq jobs"""
    
    def __init__(self):
        self.redis_pool = None
        self.logger = logger
    
    async def get_redis(self) -> ArqRedis:
        """Get Redis connection"""
        if not self.redis_pool:
            self.redis_pool = await get_redis_pool()
        return self.redis_pool
    
    async def enqueue_kyc_verification(
        self,
        verification_id: str,
        user_id: str,
        additional_data: Optional[Dict[str, Any]] = None,
        job_timeout: Optional[int] = None,
        defer_until: Optional[datetime] = None
    ) -> Job:
        """
        Enqueue KYC verification job
        
        Args:
            verification_id: Verification ID
            user_id: User ID
            additional_data: Additional verification data
            job_timeout: Job timeout in seconds
            defer_until: When to start the job
            
        Returns:
            Arq Job instance
        """
        try:
            redis = await self.get_redis()
            
            job = await redis.enqueue_job(
                'run_kyc_verification',
                verification_id=verification_id,
                user_id=user_id,
                additional_data=additional_data,
                # _job_timeout=job_timeout,
                # _defer_until=defer_until
            )
            
            self.logger.info(f"Enqueued KYC verification job {job.job_id} for verification {verification_id}")
            return job
            
        except Exception as e:
            self.logger.error(f"Error enqueuing KYC verification job: {str(e)}")
            raise
    
    async def enqueue_business_verification(
        self,
        verification_id: str,
        business_id: str,
        additional_data: Optional[Dict[str, Any]] = None,
        job_timeout: Optional[int] = None,
        defer_until: Optional[datetime] = None
    ) -> Job:
        """
        Enqueue business verification job
        
        Args:
            verification_id: Verification ID
            business_id: Business ID
            additional_data: Additional verification data
            job_timeout: Job timeout in seconds
            defer_until: When to start the job
            
        Returns:
            Arq Job instance
        """
        try:
            redis = await self.get_redis()
            
            job = await redis.enqueue_job(
                'run_business_verification',
                verification_id=verification_id,
                business_id=business_id,
                additional_data=additional_data
                # _job_timeout=job_timeout,
                # _defer_until=defer_until
            )
            
            self.logger.info(f"Enqueued business verification job {job.job_id} for verification {verification_id}")
            return job
            
        except Exception as e:
            self.logger.error(f"Error enqueuing business verification job: {str(e)}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status information
        """
        try:

            redis = await self.get_redis()
            job = Job(job_id, redis)

            status = await job.status()

            result = await job.result()

            
            return {
                "job_id": job_id,
                "status": status,
                "result": result,
                "enqueue_time": job.enqueue_time,
                "start_time": job.start_time,
                "finish_time": job.finish_time,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting job status: {str(e)}")
            return None
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            redis = await self.get_redis()
            job = Job(job_id, redis)
            
            await job.abort()
            self.logger.info(f"Cancelled job {job_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling job {job_id}: {str(e)}")
            return False
    
    async def get_queue_info(self) -> Dict[str, Any]:
        """
        Get queue information
        
        Returns:
            Queue status information
        """
        try:
            redis = await self.get_redis()
            
            # Get queue length
            queue_length = await redis.llen('arq:queue')
            
            # Get worker information (this is a simplified version)
            # In a real implementation, you might want to track workers separately
            
            return {
                "queue_length": queue_length,
                "redis_info": "connected"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting queue info: {str(e)}")
            return {"error": str(e)}
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_pool:
            await self.redis_pool.close()


# Singleton instance
job_service = JobService()