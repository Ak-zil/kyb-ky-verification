import asyncio
import uuid
from typing import Any, Dict, List, Optional

from arq import ArqRedis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.integrations.database import Database
from app.integrations.external_database import external_db
from app.integrations.persona import persona_client
from app.integrations.sift import sift_client
from app.services.agent_factory import AgentFactory
from app.utils.llm import bedrock_client
from app.utils.logging import get_logger

logger = get_logger("verification_worker")

# Create async engine for worker
worker_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Create async session factory for worker
WorkerSession = sessionmaker(
    worker_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_worker_db_session() -> AsyncSession:
    """Get database session for worker"""
    async with WorkerSession() as session:
        try:
            yield session
        finally:
            await session.close()


async def run_kyc_verification(
    ctx: Dict[str, Any],
    verification_id: str,
    user_id: str,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run KYC verification workflow in Arq worker
    
    Args:
        ctx: Arq context
        verification_id: ID of the verification
        user_id: ID of the user to verify
        additional_data: Additional data for verification
        
    Returns:
        Dict containing workflow results
    """
    try:
        ctx['logger'].info(f"Starting KYC verification workflow for {verification_id}")
        
        # Get database session
        async with WorkerSession() as db_session:
            db_client = Database(db_session)
            
            # Update verification status to processing
            await db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            
            # Initialize agent factory
            agent_factory = AgentFactory(
                db_client=db_client,
                bedrock_client=bedrock_client,
                persona_client=persona_client,
                sift_client=sift_client
            )
            
            # 1. Data Acquisition
            logger.info(f"Starting data acquisition for KYC verification {verification_id}")
            data_acquisition_agent = agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                user_id=user_id
            )
            data_result = await data_acquisition_agent.run()
            
            # Store data acquisition result
            await db_client.store_agent_result(verification_id, data_result)
            
            # If data acquisition failed, end verification
            if data_result["status"] == "error":
                logger.error(f"Data acquisition failed for KYC verification {verification_id}: {data_result['details']}")
                await db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return {"status": "failed", "reason": "Data acquisition failed"}
            
            # 2. Run verification agents in parallel
            logger.info(f"Running verification agents for KYC verification {verification_id}")
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
                agent = agent_factory.create_agent(
                    agent_type=agent_type,
                    verification_id=verification_id
                )
                agent_tasks.append(agent.run())
            
            # Run all agents in parallel
            logger.info(f"Executing {len(agent_tasks)} KYC verification agents in parallel")
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Process and store agent results
            successful_results = []
            error_agents = []
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    # Handle exception
                    logger.error(f"Agent {kyc_agent_types[i]} failed: {str(result)}")
                    error_agents.append(kyc_agent_types[i])
                    error_result = {
                        "agent_type": kyc_agent_types[i],
                        "status": "error",
                        "details": f"Agent execution error: {str(result)}",
                        "checks": []
                    }
                    await db_client.store_agent_result(verification_id, error_result)
                else:
                    # Store successful result
                    logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    await db_client.store_agent_result(verification_id, result)
                    successful_results.append(result)
            
            # 3. Run result compilation agent
            logger.info(f"Running result compilation for KYC verification {verification_id}")
            compilation_agent = agent_factory.create_agent(
                agent_type="ResultCompilation",
                verification_id=verification_id
            )
            final_result = await compilation_agent.run()
            
            # Store final result
            await db_client.store_agent_result(verification_id, final_result)
            
            # Update verification status
            verification_status = "completed"
            verification_result = final_result.get("verification_result", "failed")
            
            await db_client.update_verification_status(
                verification_id=verification_id,
                status=verification_status,
                result=verification_result,
                reason=final_result.get("reasoning", "")
            )
            
            logger.info(f"KYC verification {verification_id} completed with result: {verification_result}")
            
            return {
                "status": "completed",
                "verification_id": verification_id,
                "result": verification_result,
                "reasoning": final_result.get("reasoning", "")
            }
            
    except Exception as e:
        logger.error(f"Error in KYC verification workflow: {str(e)}")
        
        # Update verification as failed
        try:
            async with WorkerSession() as db_session:
                db_client = Database(db_session)
                await db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason=f"Workflow error: {str(e)}"
                )
        except Exception as db_error:
            logger.error(f"Failed to update verification status: {str(db_error)}")
        
        return {"status": "failed", "error": str(e)}


async def run_business_verification(
    ctx: Dict[str, Any],
    verification_id: str,
    business_id: str,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run KYB verification workflow in Arq worker
    
    Args:
        ctx: Arq context
        verification_id: ID of the verification
        business_id: ID of the business to verify
        additional_data: Additional data for verification
        
    Returns:
        Dict containing workflow results
    """
    try:
        logger.info(f"Starting KYB verification workflow for {verification_id}")
        
        # Get database session
        async with WorkerSession() as db_session:
            db_client = Database(db_session)
            
            # Update verification status to processing
            await db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            
            # Initialize agent factory
            agent_factory = AgentFactory(
                db_client=db_client,
                bedrock_client=bedrock_client,
                persona_client=persona_client,
                sift_client=sift_client
            )
            
            # 1. Data Acquisition
            logger.info(f"Starting data acquisition for KYB verification {verification_id}")
            data_acquisition_agent = agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                business_id=business_id
            )
            data_result = await data_acquisition_agent.run()
            
            # Store data acquisition result
            await db_client.store_agent_result(verification_id, data_result)
            
            # If data acquisition failed, end verification
            if data_result["status"] == "error":
                logger.error(f"Data acquisition failed for KYB verification {verification_id}: {data_result['details']}")
                await db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return {"status": "failed", "reason": "Data acquisition failed"}
                
            # 2. Extract UBOs and queue KYC verification for each
            logger.info(f"Extracting UBOs for KYB verification {verification_id}")
            business_data = data_result.get("data", {}).get("business", {})
            ubos = business_data.get("ubos", [])
            
            logger.info(f"Found {len(ubos)} UBOs for KYB verification {verification_id}")
            
            # Queue KYC verification for each UBO
            ubo_verification_ids = []
            redis = ctx.get('redis')  # Get Redis connection from context
            
            for ubo in ubos:
                ubo_user_id = ubo.get("ubo_info", {}).get("created_for_id")
                if ubo_user_id:
                    logger.info(f"Queueing KYC verification for UBO {ubo_user_id}")
                    
                    # Generate UBO verification ID
                    ubo_verification_id = str(uuid.uuid4())
                    
                    # Create UBO verification record
                    await db_client.create_verification(
                        verification_id=ubo_verification_id,
                        user_id=str(ubo_user_id),
                        business_id=None,
                        status="queued"
                    )
                    
                    # Store UBO verification reference
                    await db_client.store_ubo_verifications(
                        verification_id=verification_id,
                        ubo_verifications=[{
                            "ubo_user_id": str(ubo_user_id),
                            "verification_id": ubo_verification_id
                        }]
                    )
                    
                    # Queue UBO KYC verification
                    if redis:
                        await redis.enqueue_job(
                            'run_kyc_verification',
                            verification_id=ubo_verification_id,
                            user_id=str(ubo_user_id),
                            additional_data={
                                "ubo_info": ubo.get("ubo_info", {}),
                                "parent_business_id": business_id,
                                "ubo_role": "UBO"
                            }
                        )
                    
                    ubo_verification_ids.append(ubo_verification_id)
            
            # 3. Run KYB verification agents in parallel
            logger.info(f"Running verification agents for KYB verification {verification_id}")
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
                agent = agent_factory.create_agent(
                    agent_type=agent_type,
                    verification_id=verification_id
                )
                agent_tasks.append(agent.run())
            
            # Run all agents in parallel
            logger.info(f"Executing {len(agent_tasks)} KYB verification agents in parallel")
            agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            # Process and store agent results
            for i, result in enumerate(agent_results):
                if isinstance(result, Exception):
                    # Handle exception
                    logger.error(f"Agent {kyb_agent_types[i]} failed: {str(result)}")
                    error_result = {
                        "agent_type": kyb_agent_types[i],
                        "status": "error",
                        "details": f"Agent execution error: {str(result)}",
                        "checks": []
                    }
                    await db_client.store_agent_result(verification_id, error_result)
                else:
                    # Store successful result
                    logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    await db_client.store_agent_result(verification_id, result)
            
            # 4. Wait for UBO verifications to complete (with timeout)
            logger.info(f"Waiting for {len(ubo_verification_ids)} UBO verifications to complete")
            await _wait_for_ubo_verifications(db_client, ubo_verification_ids, timeout_minutes=30)
            
            # 5. Compile final business verification result
            logger.info(f"Running business result compilation for KYB verification {verification_id}")
            business_result_agent = agent_factory.create_agent(
                agent_type="BusinessResultCompilation",
                verification_id=verification_id,
                ubo_verification_ids=ubo_verification_ids
            )
            business_final_result = await business_result_agent.run()
            
            # Store business final result
            await db_client.store_agent_result(verification_id, business_final_result)
            
            # Update verification status
            verification_status = "completed"
            verification_result = business_final_result.get("verification_result", "failed")
            
            await db_client.update_verification_status(
                verification_id=verification_id,
                status=verification_status,
                result=verification_result,
                reason=business_final_result.get("reasoning", "")
            )
            
            logger.info(f"KYB verification {verification_id} completed with result: {verification_result}")
            
            return {
                "status": "completed",
                "verification_id": verification_id,
                "result": verification_result,
                "reasoning": business_final_result.get("reasoning", ""),
                "ubo_verifications": ubo_verification_ids
            }
            
    except Exception as e:
        logger.error(f"Error in business verification workflow: {str(e)}")
        
        # Update verification as failed
        try:
            async with WorkerSession() as db_session:
                db_client = Database(db_session)
                await db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason=f"Workflow error: {str(e)}"
                )
        except Exception as db_error:
            logger.error(f"Failed to update verification status: {str(db_error)}")
        
        return {"status": "failed", "error": str(e)}


async def run_agent_verification(
    ctx: Dict[str, Any],
    verification_id: str,
    agent_type: str,
    agent_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run individual agent verification
    
    Args:
        ctx: Arq context
        verification_id: ID of the verification
        agent_type: Type of agent to run
        agent_config: Agent configuration
        
    Returns:
        Dict containing agent results
    """
    try:
        logger.info(f"Running {agent_type} agent for verification {verification_id}")
        
        async with WorkerSession() as db_session:
            db_client = Database(db_session)
            
            # Initialize agent factory
            agent_factory = AgentFactory(
                db_client=db_client,
                bedrock_client=bedrock_client,
                persona_client=persona_client,
                sift_client=sift_client
            )
            
            # Create and run agent
            agent = agent_factory.create_agent(
                agent_type=agent_type,
                verification_id=verification_id,
                **agent_config
            )
            
            result = await agent.run()
            
            # Store agent result
            await db_client.store_agent_result(verification_id, result)
            
            logger.info(f"Agent {agent_type} completed with status: {result.get('status')}")
            return result
            
    except Exception as e:
        logger.error(f"Error running {agent_type} agent: {str(e)}")
        return {"status": "error", "error": str(e)}


async def _wait_for_ubo_verifications(
    db_client: Database,
    ubo_verification_ids: List[str],
    timeout_minutes: int = 30
) -> None:
    """
    Wait for UBO verifications to complete
    
    Args:
        db_client: Database client
        ubo_verification_ids: List of UBO verification IDs
        timeout_minutes: Timeout in minutes
    """
    timeout_seconds = timeout_minutes * 60
    check_interval = 30  # Check every 30 seconds
    elapsed_time = 0
    
    while elapsed_time < timeout_seconds:
        completed_count = 0
        
        for verification_id in ubo_verification_ids:
            verification = await db_client.get_verification(verification_id)
            if verification and verification.status in ["completed", "failed"]:
                completed_count += 1
        
        if completed_count == len(ubo_verification_ids):
            logger.info(f"All {len(ubo_verification_ids)} UBO verifications completed")
            return
        
        logger.info(f"Waiting for UBO verifications: {completed_count}/{len(ubo_verification_ids)} completed")
        await asyncio.sleep(check_interval)
        elapsed_time += check_interval
    
    logger.warning(f"Timeout waiting for UBO verifications after {timeout_minutes} minutes")