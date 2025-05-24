import asyncio
import uuid
from typing import Any, Dict, List, Optional

from celery import current_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.integrations.database_sync import SyncDatabase
from app.services.agent_factory_sync import SyncAgentFactory
from app.utils.llm_sync import SyncBedrockClient
from app.integrations.persona_sync import SyncPersonaClient
from app.integrations.sift_sync import SyncSiftClient
from app.utils.logging import get_logger

logger = get_logger("verification_tasks")

# Create synchronous database engine for Celery tasks
sync_engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI).replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_recycle=300
)
SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_sync_services():
    """Get synchronous services for Celery tasks"""
    db = SyncSessionLocal()
    try:
        db_client = SyncDatabase(db)
        bedrock_client = SyncBedrockClient()
        persona_client = SyncPersonaClient()
        sift_client = SyncSiftClient()
        
        agent_factory = SyncAgentFactory(
            db_client=db_client,
            bedrock_client=bedrock_client,
            persona_client=persona_client,
            sift_client=sift_client
        )
        
        return db_client, agent_factory
    except Exception as e:
        db.close()
        raise e


@celery_app.task(bind=True, name="run_kyc_verification")
def run_kyc_verification(self, verification_id: str, user_id: str):
    """
    Celery task for KYC verification workflow
    """
    try:
        logger.info(f"Starting KYC verification task for {verification_id}")
        
        db_client, agent_factory = get_sync_services()
        
        try:
            # Update verification status
            db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            
            # 1. Data Acquisition
            logger.info(f"Starting data acquisition for KYC verification {verification_id}")
            data_acquisition_agent = agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                user_id=user_id
            )
            data_result = data_acquisition_agent.run()
            
            # Store data acquisition result
            db_client.store_agent_result(verification_id, data_result)
            
            if data_result["status"] == "error":
                logger.error(f"Data acquisition failed for KYC verification {verification_id}")
                db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return {"status": "failed", "reason": "Data acquisition failed"}
            
            # 2. Run verification agents
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
            
            # Update task progress
            self.update_state(
                state='PROGRESS',
                meta={'current': 1, 'total': len(kyc_agent_types) + 2, 'status': 'Running verification agents'}
            )
            
            # Run agents sequentially (can be parallelized with group tasks if needed)
            successful_results = []
            for i, agent_type in enumerate(kyc_agent_types):
                try:
                    agent = agent_factory.create_agent(
                        agent_type=agent_type,
                        verification_id=verification_id
                    )
                    result = agent.run()
                    
                    logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    db_client.store_agent_result(verification_id, result)
                    successful_results.append(result)
                    
                    # Update progress
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': i + 2, 
                            'total': len(kyc_agent_types) + 2, 
                            'status': f'Completed {agent_type}'
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Agent {agent_type} failed: {str(e)}")
                    error_result = {
                        "agent_type": agent_type,
                        "status": "error",
                        "details": f"Agent execution error: {str(e)}",
                        "checks": []
                    }
                    db_client.store_agent_result(verification_id, error_result)
            
            # 3. Result compilation
            logger.info(f"Running result compilation for KYC verification {verification_id}")
            compilation_agent = agent_factory.create_agent(
                agent_type="ResultCompilation",
                verification_id=verification_id
            )
            final_result = compilation_agent.run()
            
            # Store final result
            db_client.store_agent_result(verification_id, final_result)
            
            # Update verification status
            verification_result = final_result.get("verification_result", "failed")
            db_client.update_verification_status(
                verification_id=verification_id,
                status="completed",
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
            
        finally:
            db_client.close()
            
    except Exception as e:
        logger.error(f"Error in KYC verification task: {str(e)}")
        
        # Try to update verification status to failed
        try:
            db_client, _ = get_sync_services()
            db_client.update_verification_status(
                verification_id=verification_id,
                status="failed",
                result="failed",
                reason=f"Task error: {str(e)}"
            )
            db_client.close()
        except:
            pass
            
        raise


@celery_app.task(bind=True, name="run_business_verification")
def run_business_verification(self, verification_id: str, business_id: str):
    """
    Celery task for KYB verification workflow
    """
    try:
        logger.info(f"Starting KYB verification task for {verification_id}")
        
        db_client, agent_factory = get_sync_services()
        
        try:
            # Update verification status
            db_client.update_verification_status(
                verification_id=verification_id,
                status="processing"
            )
            
            # 1. Data Acquisition
            logger.info(f"Starting data acquisition for KYB verification {verification_id}")
            data_acquisition_agent = agent_factory.create_agent(
                agent_type="DataAcquisition",
                verification_id=verification_id,
                business_id=business_id
            )
            data_result = data_acquisition_agent.run()
            
            # Store data acquisition result
            db_client.store_agent_result(verification_id, data_result)
            
            if data_result["status"] == "error":
                logger.error(f"Data acquisition failed for KYB verification {verification_id}")
                db_client.update_verification_status(
                    verification_id=verification_id,
                    status="failed",
                    result="failed",
                    reason="Data acquisition failed"
                )
                return {"status": "failed", "reason": "Data acquisition failed"}
            
            # 2. Extract UBOs and start KYC verifications
            business_data = data_result.get("data", {}).get("business", {})
            ubos = business_data.get("ubos", [])
            
            logger.info(f"Found {len(ubos)} UBOs for KYB verification {verification_id}")
            
            # Start UBO verifications as separate Celery tasks
            ubo_verification_tasks = []
            for ubo in ubos:
                ubo_user_id = ubo.get("ubo_info", {}).get("created_for_id")
                if ubo_user_id:
                    ubo_verification_id = str(uuid.uuid4())
                    
                    # Create UBO verification record
                    db_client.create_verification(
                        verification_id=ubo_verification_id,
                        user_id=str(ubo_user_id),
                        status="pending"
                    )
                    
                    # Store UBO verification reference
                    db_client.store_ubo_verifications(
                        verification_id=verification_id,
                        ubo_verifications=[{
                            "ubo_user_id": str(ubo_user_id),
                            "verification_id": ubo_verification_id
                        }]
                    )
                    
                    # Start UBO KYC verification task
                    task = run_kyc_verification.delay(ubo_verification_id, str(ubo_user_id))
                    ubo_verification_tasks.append({
                        "task_id": task.id,
                        "verification_id": ubo_verification_id,
                        "ubo_user_id": str(ubo_user_id)
                    })
            
            # 3. Run KYB verification agents
            logger.info(f"Running verification agents for KYB verification {verification_id}")
            kyb_agent_types = [
                "NormalDiligence",
                "IrsMatchAgent",
                "SosFilingsAgent",
                "EinLetterAgent",
                "ArticlesIncorporationAgent"
            ]
            
            for agent_type in kyb_agent_types:
                try:
                    agent = agent_factory.create_agent(
                        agent_type=agent_type,
                        verification_id=verification_id
                    )
                    result = agent.run()
                    
                    logger.info(f"Agent {result['agent_type']} completed with status: {result['status']}")
                    db_client.store_agent_result(verification_id, result)
                    
                except Exception as e:
                    logger.error(f"Agent {agent_type} failed: {str(e)}")
                    error_result = {
                        "agent_type": agent_type,
                        "status": "error",
                        "details": f"Agent execution error: {str(e)}",
                        "checks": []
                    }
                    db_client.store_agent_result(verification_id, error_result)
            
            # 4. Wait for UBO verifications to complete
            logger.info(f"Waiting for {len(ubo_verification_tasks)} UBO verifications to complete")
            
            # For simplicity, we'll check UBO task status periodically
            # In production, you might want to use Celery's chord or group for better coordination
            import time
            max_wait_time = 300  # 5 minutes
            check_interval = 10  # 10 seconds
            waited_time = 0
            
            while waited_time < max_wait_time:
                all_completed = True
                for ubo_task in ubo_verification_tasks:
                    verification = db_client.get_verification(ubo_task["verification_id"])
                    if verification and verification.status not in ["completed", "failed"]:
                        all_completed = False
                        break
                
                if all_completed:
                    break
                    
                time.sleep(check_interval)
                waited_time += check_interval
            
            # 5. Compile business verification results
            logger.info(f"Running business result compilation for KYB verification {verification_id}")
            
            ubo_verification_ids = [task["verification_id"] for task in ubo_verification_tasks]
            business_result_agent = agent_factory.create_agent(
                agent_type="BusinessResultCompilation",
                verification_id=verification_id,
                ubo_verification_ids=ubo_verification_ids
            )
            business_final_result = business_result_agent.run()
            
            # Store business final result
            db_client.store_agent_result(verification_id, business_final_result)
            
            # Update verification status
            verification_result = business_final_result.get("verification_result", "failed")
            db_client.update_verification_status(
                verification_id=verification_id,
                status="completed",
                result=verification_result,
                reason=business_final_result.get("reasoning", "")
            )
            
            logger.info(f"KYB verification {verification_id} completed with result: {verification_result}")
            
            return {
                "status": "completed",
                "verification_id": verification_id,
                "result": verification_result,
                "reasoning": business_final_result.get("reasoning", "")
            }
            
        finally:
            db_client.close()
            
    except Exception as e:
        logger.error(f"Error in KYB verification task: {str(e)}")
        
        # Try to update verification status to failed
        try:
            db_client, _ = get_sync_services()
            db_client.update_verification_status(
                verification_id=verification_id,
                status="failed",
                result="failed",
                reason=f"Task error: {str(e)}"
            )
            db_client.close()
        except:
            pass
            
        raise