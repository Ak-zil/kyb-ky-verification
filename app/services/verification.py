import uuid
from typing import Any, Dict, Optional

from app.services.agent_factory import AgentFactory
from fastapi import BackgroundTasks

from app.core.exceptions import VerificationError
from app.integrations.database import Database
from app.services.job_service import job_service
from app.utils.logging import get_logger


class VerificationWorkflowService:
    """Service for managing verification workflows using Arq"""

    def __init__(
        self, 
        db_client: Database,
        agent_factory: AgentFactory,
        background_tasks: BackgroundTasks = None  # Keep for compatibility but not used
    ):
        """
        Initialize verification workflow service
        
        Args:
            db_client: Database client
            background_tasks: FastAPI background tasks (deprecated)
        """
        self.db_client = db_client
        self.logger = get_logger("VerificationWorkflow")
        
    async def start_kyc_verification(
        self, 
        user_id: str, 
        parent_verification_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start KYC verification workflow using Arq
        
        Args:
            user_id: ID of the user to verify
            parent_verification_id: ID of parent verification (for UBO verification)
            additional_data: Additional data for verification
            
        Returns:
            Verification ID
            
        Raises:
            VerificationError: If verification cannot be started
        """
        try:
            # Generate verification ID
            verification_id = str(uuid.uuid4())
            
            # Create verification record
            await self.db_client.create_verification(
                verification_id=verification_id,
                user_id=user_id,
                business_id=None,
                status="queued"  # Changed from "in_progress" to "queued"
            )
            
            # If this is a UBO verification, link it to the parent
            if parent_verification_id:
                await self.db_client.store_ubo_verifications(
                    verification_id=parent_verification_id,
                    ubo_verifications=[{
                        "ubo_user_id": user_id,
                        "verification_id": verification_id
                    }]
                )
            
            # Store additional data if provided
            if additional_data:
                await self.db_client.store_verification_data(
                    verification_id=verification_id,
                    data_type="additional_data",
                    data=additional_data
                )
            
            # Enqueue verification job
            job = await job_service.enqueue_kyc_verification(
                verification_id=verification_id,
                user_id=user_id,
                additional_data=additional_data
            )
            
            self.logger.info(f"Enqueued KYC verification {verification_id} as job {job.job_id}")
            
            return verification_id
            
        except Exception as e:
            self.logger.error(f"Error starting KYC verification: {str(e)}")
            raise VerificationError(f"Error starting KYC verification: {str(e)}")
    
    async def start_business_verification(
        self, 
        business_id: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start KYB verification workflow using Arq
        
        Args:
            business_id: ID of the business to verify
            additional_data: Additional data for verification
            
        Returns:
            Verification ID
            
        Raises:
            VerificationError: If verification cannot be started
        """
        try:
            # Generate verification ID
            verification_id = str(uuid.uuid4())
            
            # Create verification record
            await self.db_client.create_verification(
                verification_id=verification_id,
                user_id=None,
                business_id=business_id,
                status="queued"  # Changed from "in_progress" to "queued"
            )
            
            # Store additional data if provided
            if additional_data:
                await self.db_client.store_verification_data(
                    verification_id=verification_id,
                    data_type="additional_data",
                    data=additional_data
                )
            
            # Enqueue verification job
            job = await job_service.enqueue_business_verification(
                verification_id=verification_id,
                business_id=business_id,
                additional_data=additional_data
            )
            
            self.logger.info(f"Enqueued business verification {verification_id} as job {job.job_id}")
            
            return verification_id
            
        except Exception as e:
            self.logger.error(f"Error starting business verification: {str(e)}")
            raise VerificationError(f"Error starting business verification: {str(e)}")