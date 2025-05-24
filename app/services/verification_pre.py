import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import BackgroundTasks

from app.core.exceptions import VerificationError
from app.integrations.database import Database
from app.services.agent_factory import AgentFactory
from app.utils.logging import get_logger


class VerificationWorkflowService:
    """Service for managing verification workflows"""

    def __init__(
        self, 
        db_client: Database, 
        agent_factory: AgentFactory,
        background_tasks: BackgroundTasks
    ):
        """
        Initialize verification workflow service
        
        Args:
            db_client: Database client
            agent_factory: Agent factory
            background_tasks: FastAPI background tasks
        """
        self.db_client = db_client
        self.agent_factory = agent_factory
        self.background_tasks = background_tasks
        self.logger = get_logger("VerificationWorkflow")
        
    async def start_kyc_verification(
        self, 
        user_id: str, 
        parent_verification_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start KYC verification workflow
        
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
                status="in_progress"
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
            # Start background task for verification
            self.background_tasks.add_task(
                self._run_kyc_verification_workflow, 
                verification_id=verification_id,
                user_id=user_id
            )
            
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
        Start KYB verification workflow
        
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
                status="in_progress"
            )
            
            # Store additional data if provided
            if additional_data:
                await self.db_client.store_verification_data(
                    verification_id=verification_id,
                    data_type="additional_data",
                    data=additional_data
                )
            
            # Start background task for verification
            self.background_tasks.add_task(
                self._run_business_verification_workflow, 
                verification_id=verification_id,
                business_id=business_id
            )
            
            return verification_id
            
        except Exception as e:
            self.logger.error(f"Error starting business verification: {str(e)}")
            raise VerificationError(f"Error starting business verification: {str(e)}")
    
    async def _run_kyc_verification_workflow(self, verification_id: str, user_id: str):
        """
        Execute KYC verification workflow
        
        Args:
            verification_id: ID of the verification
            user_id: ID of the user to verify
        """
        try:
            self.logger.info("starting db update")
            # Update verification status to processing
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            self.logger.info("end db update")
            # 1. Data Acquisition
            self.logger.info(f"Starting data acquisition for KYC verification {verification_id}")
            data_acquisition_agent = self.agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                user_id=user_id
            )
            data_result = await data_acquisition_agent.run()
            
            # Store data acquisition result
            await self.db_client.store_agent_result(verification_id, data_result)
            
            # If data acquisition failed, end verification
            if data_result["status"] == "error":
                self.logger.error(f"Data acquisition failed for KYC verification {verification_id}: {data_result['details']}")
                await self.db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return
            
            # 2. Run verification agents in parallel
            self.logger.info(f"Running verification agents for KYC verification {verification_id}")
            kyc_agent_types = [
                "InitialDiligence",
                "GovtIdVerification",
                "IdSelfieVerification",
                "AamvaVerification",
                "EmailPhoneIpVerification",
                "PaymentBehaviorAgent",
                "LoginActivitiesAgent",
                "SiftVerificationAgent",
                "IdCheckAgent",
                "OfacVerificationAgent"
            ]
            
            # Create tasks for all agents
            agent_tasks = []
            for agent_type in kyc_agent_types:
                agent = self.agent_factory.create_agent(
                    agent_type=agent_type,
                    verification_id=verification_id
                )
                agent_tasks.append(agent.run())
            
            # Run all agents in parallel
            self.logger.info(f"Executing {len(agent_tasks)} KYC verification agents in parallel")
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Process and store agent results
            successful_results = []
            error_agents = []
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    # Handle exception
                    self.logger.error(f"Agent {kyc_agent_types[i]} failed: {str(result)}")
                    error_agents.append(kyc_agent_types[i])
                    error_result = {
                        "agent_type": kyc_agent_types[i],
                        "status": "error",
                        "details": f"Agent execution error: {str(result)}",
                        "checks": []
                    }
                    await self.db_client.store_agent_result(verification_id, error_result)
                else:
                    # Store successful result
                    self.logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    await self.db_client.store_agent_result(verification_id, result)
                    successful_results.append(result)
            
            # 3. Run result compilation agent
            self.logger.info(f"Running result compilation for KYC verification {verification_id}")
            compilation_agent = self.agent_factory.create_agent(
                agent_type="ResultCompilation",
                verification_id=verification_id
            )
            final_result = await compilation_agent.run()
            
            # Store final result
            await self.db_client.store_agent_result(verification_id, final_result)
            
            # Update verification status
            verification_status = "completed"
            verification_result = final_result.get("verification_result", "failed")
            
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status=verification_status,
                result=verification_result,
                reason=final_result.get("reasoning", "")
            )
            
            self.logger.info(f"KYC verification {verification_id} completed with result: {verification_result}")
            
        except Exception as e:
            self.logger.error(f"Error in KYC verification workflow: {str(e)}")
            # Update verification as failed
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status="failed",
                result="failed",
                reason=f"Workflow error: {str(e)}"
            )
    
    async def _run_business_verification_workflow(self, verification_id: str, business_id: str):
        """
        Execute KYB verification workflow
        
        Args:
            verification_id: ID of the verification
            business_id: ID of the business to verify
        """
        try:
            # Update verification status to processing
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            
            # 1. Data Acquisition
            self.logger.info(f"Starting data acquisition for KYB verification {verification_id}")
            data_acquisition_agent = self.agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                business_id=business_id
            )
            data_result = await data_acquisition_agent.run()
            
            # Store data acquisition result
            await self.db_client.store_agent_result(verification_id, data_result)
            
            # If data acquisition failed, end verification
            if data_result["status"] == "error":
                self.logger.error(f"Data acquisition failed for KYB verification {verification_id}: {data_result['details']}")
                await self.db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return
                
            # 2. Extract UBOs and start KYC verification for each
            self.logger.info(f"Extracting UBOs for KYB verification {verification_id}")
            business_data = data_result.get("data", {}).get("business", {})
            ubos = business_data.get("ubos", [])
            
            self.logger.info(f"Found {len(ubos)} UBOs for KYB verification {verification_id}")
            
            # Start KYC verification for each UBO
            ubo_verification_ids = []
            for ubo in ubos:
                ubo_user_id = ubo.get("ubo_info", {}).get("created_for_id") # TODO: user_id
                if ubo_user_id:
                    self.logger.info(f"Starting KYC verification for UBO {ubo_user_id}")
                    
                    # Extract UBO-specific data
                    ubo_additional_data = {
                        "ubo_info": ubo.get("ubo_info", {}),
                        "parent_business_id": business_id,
                        "ubo_role": "UBO"
                    }
                    
                    ubo_verification_id = await self.start_kyc_verification(
                        user_id=str(ubo_user_id),
                        parent_verification_id=verification_id,
                        additional_data=ubo_additional_data
                    )
                    
                    ubo_verification_ids.append({
                        "ubo_user_id": ubo_user_id,
                        "verification_id": ubo_verification_id
                    })
            
            # 3. Run KYB verification agents in parallel
            self.logger.info(f"Running verification agents for KYB verification {verification_id}")
            kyb_agent_types = [
                "NormalDiligence",
                "IrsMatchAgent",
                "SosFilingsAgent",
                "EinLetterAgent",
                "ArticlesIncorporationAgent"
            ]
            
            # Create tasks for all agents
            agent_tasks = []
            for agent_type in kyb_agent_types:
                agent = self.agent_factory.create_agent(
                    agent_type=agent_type,
                    verification_id=verification_id
                )
                agent_tasks.append(agent.run())
            
            # Run all agents in parallel
            self.logger.info(f"Executing {len(agent_tasks)} KYB verification agents in parallel")
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Process and store agent results
            successful_results = []
            error_agents = []
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    # Handle exception
                    self.logger.error(f"Agent {kyb_agent_types[i]} failed: {str(result)}")
                    error_agents.append(kyb_agent_types[i])
                    error_result = {
                        "agent_type": kyb_agent_types[i],
                        "status": "error",
                        "details": f"Agent execution error: {str(result)}",
                        "checks": []
                    }
                    await self.db_client.store_agent_result(verification_id, error_result)
                else:
                    # Store successful result
                    self.logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    await self.db_client.store_agent_result(verification_id, result)
                    successful_results.append(result)
            
            # 4. Wait for all UBO verifications to complete
            self.logger.info(f"Waiting for {len(ubo_verification_ids)} UBO verifications to complete")
            ubo_verification_results = []
            for ubo_verification in ubo_verification_ids:
                ubo_verification_id = ubo_verification["verification_id"]
                ubo_user_id = ubo_verification["ubo_user_id"]
                
                self.logger.info(f"Waiting for UBO verification {ubo_verification_id} to complete")
                verification_result = await self._wait_for_verification_completion(ubo_verification_id)
                
                ubo_verification_results.append({
                    "ubo_user_id": ubo_user_id,
                    "verification_id": ubo_verification_id,
                    "status": verification_result.get("status"),
                    "result": verification_result.get("result")
                })
            
            # 5. Compile final business verification result including UBO results
            self.logger.info(f"Running business result compilation for KYB verification {verification_id}")
            business_result_agent = self.agent_factory.create_agent(
                agent_type="BusinessResultCompilation",
                verification_id=verification_id,
                ubo_verification_ids=[uv["verification_id"] for uv in ubo_verification_ids]
            )
            business_final_result = await business_result_agent.run()
            
            # Store business final result
            await self.db_client.store_agent_result(verification_id, business_final_result)
            
            # Update verification status
            verification_status = "completed"
            verification_result = business_final_result.get("verification_result", "failed")
            
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status=verification_status,
                result=verification_result,
                reason=business_final_result.get("reasoning", "")
            )
            
            self.logger.info(f"KYB verification {verification_id} completed with result: {verification_result}")
            
        except Exception as e:
            self.logger.error(f"Error in business verification workflow: {str(e)}")
            # Update verification as failed
            await self.db_client.update_verification_status(
                verification_id=verification_id,
                status="failed",
                result="failed",
                reason=f"Workflow error: {str(e)}"
            )
    
    async def _wait_for_verification_completion(self, verification_id: str, timeout_seconds: int = 300):
        """
        Wait for a verification to complete with timeout
        
        Args:
            verification_id: ID of the verification
            timeout_seconds: Timeout in seconds
            
        Returns:
            Verification record
        """
        interval_seconds = 10
        max_attempts = timeout_seconds // interval_seconds
        attempts = 0
        
        while attempts < max_attempts:
            verification = await self.db_client.get_verification(verification_id)
            
            if not verification:
                self.logger.warning(f"Verification {verification_id} not found")
                return {"status": "not_found"}
                
            status = verification.status
            
            if status in ["completed", "failed"]:
                self.logger.info(f"Verification {verification_id} completed with status: {status}")
                return verification
                
            # Wait before checking again
            self.logger.debug(f"Verification {verification_id} still in progress, waiting {interval_seconds} seconds")
            await asyncio.sleep(interval_seconds)
            attempts += 1
        
        # If we're here, we timed out
        self.logger.warning(f"Verification {verification_id} did not complete within timeout ({timeout_seconds}s)")
        return {"status": "timeout"}