from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import VerificationError, DataValidationError
from app.db.session import get_db
from app.integrations.database import Database
from app.schemas.verification import (
    KycVerificationRequest, BusinessVerificationRequest, 
    VerificationResponse, VerificationStatusResponse, VerificationReportResponse,
    VerificationListResponse, VerificationSummary
)
from app.services.apikey import APIKeyService, get_api_key, get_api_key_service
from app.services.auth import get_current_active_user, get_current_user
from app.services.verification import VerificationWorkflowService
from app.services.agent_factory import AgentFactory
from app.utils.llm import bedrock_client
from app.utils.validation import validate_verification_request
from app.integrations.persona import persona_client
from app.integrations.sift import sift_client
from app.utils.logging import get_logger
from app.models.user import User

router = APIRouter()
logger = get_logger("verify_api")


def get_verification_service(
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> VerificationWorkflowService:
    """
    Get verification workflow service
    
    Args:
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        VerificationWorkflowService
    """
    db_client = Database(db)
    agent_factory = AgentFactory(
        db_client=db_client,
        bedrock_client=bedrock_client,
        persona_client=persona_client,
        sift_client=sift_client
    )
    return VerificationWorkflowService(
        db_client=db_client,
        agent_factory=agent_factory,
        background_tasks=background_tasks
    )


@router.post("/kyc", response_model=VerificationResponse)
async def start_kyc_verification(
    request: KycVerificationRequest,
    api_key: str = Depends(get_api_key),
    verification_service: VerificationWorkflowService = Depends(get_verification_service)
) -> Any:
    """
    Start KYC verification workflow
    
    This endpoint initiates a KYC (Know Your Customer) verification process for an individual user.
    It requires a user_id and optionally accepts additional_data for verification.
    
    Args:
        request: KYC verification request containing user_id and optional additional_data
        api_key: API key for authentication
        verification_service: Verification workflow service
        
    Returns:
        VerificationResponse with verification_id and status
        
    Raises:
        HTTPException: If validation fails or verification cannot be started
    """
    try:
        logger.info(f"Starting KYC verification for user_id {request.user_id}")
        
        # Validate request
        validate_verification_request(request.dict(), "kyc")
        
        # Start verification
        verification_id = await verification_service.start_kyc_verification(
            user_id=request.user_id,
            additional_data=request.additional_data
        )
        
        logger.info(f"KYC verification started with verification_id {verification_id}")
        
        return {
            "verification_id": verification_id,
            "status": "PENDING"
        }
    except DataValidationError as e:
        logger.error(f"Validation error in KYC verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except VerificationError as e:
        logger.error(f"Verification error in KYC verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in KYC verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting verification: {str(e)}"
        )


@router.post("/business", response_model=VerificationResponse)
async def start_business_verification(
    request: BusinessVerificationRequest,
    api_key: str = Depends(get_api_key),
    verification_service: VerificationWorkflowService = Depends(get_verification_service)
) -> Any:
    """
    Start business verification workflow
    
    This endpoint initiates a KYB (Know Your Business) verification process for a business.
    It requires a business_id and optionally accepts additional_data for verification.
    
    The KYB process also initiates KYC verification for all Ultimate Beneficial Owners (UBOs)
    associated with the business.
    
    Args:
        request: Business verification request containing business_id and optional additional_data
        api_key: API key for authentication
        verification_service: Verification workflow service
        
    Returns:
        VerificationResponse with verification_id and status
        
    Raises:
        HTTPException: If validation fails or verification cannot be started
    """
    try:
        logger.info(f"Starting KYB verification for business_id {request.business_id}")
        
        # Validate request
        validate_verification_request(request.dict(), "business")
        
        # Start verification
        verification_id = await verification_service.start_business_verification(
            business_id=request.business_id,
            additional_data=request.additional_data
        )
        
        logger.info(f"KYB verification started with verification_id {verification_id}")
        
        return {
            "verification_id": verification_id,
            "status": "PENDING"
        }
    except DataValidationError as e:
        logger.error(f"Validation error in KYB verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except VerificationError as e:
        logger.error(f"Verification error in KYB verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in KYB verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting verification: {str(e)}"
        )


@router.get("/status/{verification_id}", response_model=VerificationStatusResponse)
async def get_verification_status(
    verification_id: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get status of a verification
    
    This endpoint returns the current status of a verification process.
    
    Args:
        verification_id: ID of the verification
        api_key: API key for authentication
        db: Database session
        
    Returns:
        VerificationStatusResponse with verification_id, status, created_at, and updated_at
        
    Raises:
        HTTPException: If verification not found or other error occurs
    """
    try:
        logger.info(f"Getting status for verification_id {verification_id}")
        
        
        # Get verification status
        db_client = Database(db)
        verification = await db_client.get_verification(verification_id)
        
        if not verification:
            logger.warning(f"Verification {verification_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification {verification_id} not found"
            )
        
        logger.info(f"Verification {verification_id} status: {verification.status}")
        
        return {
            "verification_id": verification_id,
            "status": verification.status,
            "created_at": verification.created_at,
            "updated_at": verification.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting verification status: {str(e)}"
        )


@router.get("/report", response_model=VerificationReportResponse)
async def get_verification_report(
    business_id: Optional[str] = None,
    user_id: Optional[str] = None,
    verification_id: Optional[str] = None,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get report for a verification
    
    This endpoint returns a detailed report for a verification process.
    It can be queried by business_id, user_id, or verification_id.
    
    Args:
        business_id: ID of the business (for KYB verification)
        user_id: ID of the user (for KYC verification)
        verification_id: ID of the verification (direct lookup)
        api_key: API key for authentication
        db: Database session
        
    Returns:
        VerificationReportResponse with verification details and results
        
    Raises:
        HTTPException: If verification not found or other error occurs
    """
    try:
        logger.info(f"Getting verification report for business_id={business_id}, user_id={user_id}, verification_id={verification_id}")
        
        if not business_id and not user_id and not verification_id:
            logger.warning("No identifiers provided for verification report")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either business_id, user_id, or verification_id must be provided"
            )
        
        db_client = Database(db)
        
        # If verification_id is provided, use it directly
        if verification_id:
            verification = await db_client.get_verification(verification_id)
            if not verification:
                logger.warning(f"Verification {verification_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Verification {verification_id} not found"
                )
        elif business_id:
            # Get business verification by business_id
            verification = await db_client.get_business_verification_by_business_id(business_id)
            if not verification:
                logger.warning(f"Verification for business {business_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Verification for business {business_id} not found"
                )
        else:
            # Get user verification by user_id
            verification = await db_client.get_user_verification_by_user_id(user_id)
            if not verification:
                logger.warning(f"Verification for user {user_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Verification for user {user_id} not found"
                )
        
        # Build the report based on the verification type
        if verification.business_id:
            # Business verification report
            return await _build_business_verification_report(db_client, verification)
        else:
            # User verification report
            return await _build_user_verification_report(db_client, verification)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting verification report: {str(e)}"
        )


# NEW ENDPOINT: List all KYC verifications
@router.get("/kyc/list", response_model=VerificationListResponse)
async def list_kyc_verifications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all KYC verifications
    
    This endpoint returns a paginated list of KYC verifications with optional status filtering.
    
    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        status: Optional filter by verification status
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        VerificationListResponse with list of verifications and total count
        
    Raises:
        HTTPException: If error occurs while fetching verifications
    """
    try:
        logger.info(f"Listing KYC verifications (skip={skip}, limit={limit}, status={status})")
        
        db_client = Database(db)
        
        # Get KYC verifications
        verifications, total = await db_client.get_verifications(
            skip=skip,
            limit=limit,
            status=status,
            verification_type="kyc"
        )
        
        # Convert to response format
        verification_summaries = []
        for verification in verifications:
            verification_summaries.append(
                VerificationSummary(
                    verification_id=verification.verification_id,
                    user_id=verification.user_id,
                    business_id=verification.business_id,
                    status=verification.status,
                    result=verification.result,
                    created_at=verification.created_at,
                    completed_at=verification.completed_at
                )
            )
        
        logger.info(f"Found {total} KYC verifications")
        
        return {
            "items": verification_summaries,
            "total": total
        }
    except Exception as e:
        logger.error(f"Error listing KYC verifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing KYC verifications: {str(e)}"
        )


# NEW ENDPOINT: List all KYB verifications
@router.get("/business/list", response_model=VerificationListResponse)
async def list_business_verifications(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all KYB verifications
    
    This endpoint returns a paginated list of KYB verifications with optional status filtering.
    
    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        status: Optional filter by verification status
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        VerificationListResponse with list of verifications and total count
        
    Raises:
        HTTPException: If error occurs while fetching verifications
    """
    try:
        logger.info(f"Listing KYB verifications (skip={skip}, limit={limit}, status={status})")
        
        db_client = Database(db)
        
        # Get KYB verifications
        verifications, total = await db_client.get_verifications(
            skip=skip,
            limit=limit,
            status=status,
            verification_type="kyb"
        )
        
        # Convert to response format
        verification_summaries = []
        for verification in verifications:
            verification_summaries.append(
                VerificationSummary(
                    verification_id=verification.verification_id,
                    user_id=verification.user_id,
                    business_id=verification.business_id,
                    status=verification.status,
                    result=verification.result,
                    created_at=verification.created_at,
                    completed_at=verification.completed_at
                )
            )
        
        logger.info(f"Found {total} KYB verifications")
        
        return {
            "items": verification_summaries,
            "total": total
        }
    except Exception as e:
        logger.error(f"Error listing KYB verifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing KYB verifications: {str(e)}"
        )


# NEW ENDPOINT: Get detailed verification report with token authentication
@router.get("/report/detail/{verification_id}", response_model=VerificationReportResponse)
async def get_detailed_verification_report(
    verification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get detailed verification report with token authentication
    
    This endpoint returns a detailed report for a verification process using token authentication.
    
    Args:
        verification_id: ID of the verification
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        VerificationReportResponse with verification details and results
        
    Raises:
        HTTPException: If verification not found or other error occurs
    """
    try:
        logger.info(f"Getting detailed verification report for verification_id={verification_id}")
        
        db_client = Database(db)
        
        # Get verification by ID
        verification = await db_client.get_verification(verification_id)
        if not verification:
            logger.warning(f"Verification {verification_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification {verification_id} not found"
            )
        
        # Build the report based on the verification type
        if verification.business_id:
            # Business verification report
            return await _build_business_verification_report(db_client, verification)
        else:
            # User verification report
            return await _build_user_verification_report(db_client, verification)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed verification report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting detailed verification report: {str(e)}"
        )


async def _build_business_verification_report(db_client: Database, verification: Any) -> VerificationReportResponse:
    """
    Build a business verification report
    
    Args:
        db_client: Database client
        verification: Verification record
        
    Returns:
        VerificationReportResponse for business verification
    """
    # Get UBO verifications
    ubo_verifications = await db_client.get_ubo_verifications_for_business(verification.verification_id)
    
    # Get all agent results
    agent_results = await db_client.get_verification_agent_results(verification.verification_id)
    
    # Get final result
    final_result = next((r for r in agent_results 
                       if r.agent_type == "BusinessResultCompilationAgent"), None)
    
    # Convert agent_results to dictionaries for report
    verification_checks = []
    for result in agent_results:
        if result.status == "success" and hasattr(result, "checks") and result.checks:
            for check in result.checks:
                verification_checks.append({
                    "agent_type": result.agent_type,
                    "check_name": check.get("name"),
                    "status": check.get("status"),
                    "details": check.get("details")
                })
    
    # Compile UBO reports
    ubo_reports = []
    for ubo in ubo_verifications:
        ubo_verification = await db_client.get_verification(ubo.ubo_verification_id)
        
        # Get overall status from verification record
        ubo_status = ubo_verification.status if ubo_verification else "unknown"
        ubo_result = ubo_verification.result if ubo_verification else None
        ubo_reason = ubo_verification.reason if ubo_verification else None
        
        ubo_reports.append({
            "user_id": ubo.ubo_user_id,
            "verification_id": ubo.ubo_verification_id,
            "status": ubo_status,
            "result": ubo_result,
            "reason": ubo_reason
        })
    
    # Get overall status - this might be stored in verification.result
    overall_status = verification.result if verification and verification.result else "unknown"
    
    # Get summary from final_result details
    summary = final_result.details if final_result else None
    
    return {
        "verification_id": verification.verification_id,
        "status": verification.status,
        "created_at": verification.created_at,
        "completed_at": verification.completed_at,
        "results": {
            "overall_status": overall_status,
            "verification_checks": verification_checks,
            "summary": summary,
            "ubo_reports": ubo_reports
        }
    }


async def _build_user_verification_report(db_client: Database, verification: Any) -> VerificationReportResponse:
    """
    Build a user verification report
    
    Args:
        db_client: Database client
        verification: Verification record
        
    Returns:
        VerificationReportResponse for user verification
    """
    # Get all agent results
    agent_results = await db_client.get_verification_agent_results(verification.verification_id)
    
    # Get final result
    final_result = next((r for r in agent_results 
                       if r.agent_type == "ResultCompilationAgent"), None)
    
    # Convert agent_results to dictionaries for report
    verification_checks = []
    for result in agent_results:
        if result.status == "success" and hasattr(result, "checks") and result.checks:
            for check in result.checks:
                verification_checks.append({
                    "agent_type": result.agent_type,
                    "check_name": check.get("name"),
                    "status": check.get("status"),
                    "details": check.get("details")
                })
    
    # Get overall status - this might be stored in verification.result
    overall_status = verification.result if verification and verification.result else "unknown"
    
    # Get summary from final_result details
    summary = final_result.details if final_result else None
    
    return {
        "verification_id": verification.verification_id,
        "status": verification.status,
        "created_at": verification.created_at,
        "completed_at": verification.completed_at,
        "results": {
            "overall_status": overall_status,
            "verification_checks": verification_checks,
            "summary": summary
        }
    }