import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, APIKey
from app.models.verification import (
    Verification, VerificationData, VerificationResult, UboVerification
)
from app.utils.json_encoder import convert_dates_to_strings
from app.utils.logging import get_logger

logger = get_logger("database")


class Database:
    """Database interface for all main application database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logger

    # User operations
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            result = await self.session.execute(
                select(User).where(User.email == email)
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error getting user by email: {str(e)}")
            raise

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        try:
            user = User(**user_data)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error creating user: {str(e)}")
            raise

    # API Key operations
    async def create_api_key(self, api_key_data: Dict[str, Any]) -> APIKey:
        """Create a new API key"""
        try:
            api_key = APIKey(**api_key_data)
            self.session.add(api_key)
            await self.session.commit()
            await self.session.refresh(api_key)
            return api_key
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error creating API key: {str(e)}")
            raise

    async def get_api_key_by_key_value(self, key_value: str) -> Optional[APIKey]:
        """Get API key by key value"""
        try:
            result = await self.session.execute(
                select(APIKey).where(APIKey.key_value == key_value)
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error getting API key: {str(e)}")
            raise

    async def get_api_keys(self, skip: int = 0, limit: int = 100) -> List[APIKey]:
        """Get all API keys"""
        try:
            result = await self.session.execute(
                select(APIKey).offset(skip).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting API keys: {str(e)}")
            raise

    async def update_api_key(self, api_key_id: int, update_data: Dict[str, Any]) -> Optional[APIKey]:
        """Update API key"""
        try:
            # Get the API key
            result = await self.session.execute(
                select(APIKey).where(APIKey.id == api_key_id)
            )
            api_key = result.scalars().first()
            
            if not api_key:
                return None
                
            # Update fields
            for key, value in update_data.items():
                setattr(api_key, key, value)
                
            await self.session.commit()
            await self.session.refresh(api_key)
            return api_key
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error updating API key: {str(e)}")
            raise

    async def delete_api_key(self, api_key_id: int) -> bool:
        """Delete API key"""
        try:
            # Get the API key
            result = await self.session.execute(
                select(APIKey).where(APIKey.id == api_key_id)
            )
            api_key = result.scalars().first()
            
            if not api_key:
                return False
                
            # Delete the API key
            await self.session.delete(api_key)
            await self.session.commit()
            return True
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error deleting API key: {str(e)}")
            raise

    # Verification operations
    async def create_verification(
        self, 
        verification_id: str, 
        user_id: Optional[str] = None, 
        business_id: Optional[str] = None, 
        status: str = "pending"
    ) -> Verification:
        """Create a new verification"""
        try:
            verification = Verification(
                verification_id=verification_id,
                user_id=user_id,
                business_id=business_id,
                status=status
            )
            self.session.add(verification)
            await self.session.commit()
            await self.session.refresh(verification)
            return verification
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error creating verification: {str(e)}")
            raise

    async def get_verification(self, verification_id: str) -> Optional[Verification]:
        """Get verification by ID"""
        try:
            result = await self.session.execute(
                select(Verification).where(Verification.verification_id == verification_id)
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error getting verification: {str(e)}")
            raise

    async def update_verification_status(
        self, 
        verification_id: str, 
        status: str,
        result: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[Verification]:
        """Update verification status"""
        try:
            # Get the verification
            query_result  = await self.session.execute(
                select(Verification).where(Verification.verification_id == verification_id)
            )
            verification = query_result.scalars().first()
            
            if not verification:
                return None
                
            # Update fields
            verification.status = status
            if result:
                verification.result = result
            if reason:
                verification.reason = reason
                
            # If status is completed or failed, set completed_at
            if status in ["completed", "failed"]:
                verification.completed_at = datetime.utcnow() # datetime.now(datetime.timezone.utc)
                
            await self.session.commit()
            await self.session.refresh(verification)
            return verification
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error updating verification status: {str(e)}")
            raise

    from app.utils.json_encoder import convert_dates_to_strings

    async def store_verification_data(
        self, 
        verification_id: str, 
        data_type: str, 
        data: Dict[str, Any]
    ) -> VerificationData:
        """Store verification data"""
        try:
            # Convert dates to strings
            json_safe_data = convert_dates_to_strings(data)
            
            verification_data = VerificationData(
                verification_id=verification_id,
                data_type=data_type,
                data=json_safe_data
            )
            self.session.add(verification_data)
            await self.session.commit()
            await self.session.refresh(verification_data)
            return verification_data
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error storing verification data: {str(e)}")
            raise

    async def get_verification_data(
        self, 
        verification_id: str, 
        data_type: Optional[str] = None
    ) -> List[VerificationData]:
        """Get verification data"""
        try:
            query = select(VerificationData).where(
                VerificationData.verification_id == verification_id
            )
            
            if data_type:
                query = query.where(VerificationData.data_type == data_type)
                
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting verification data: {str(e)}")
            raise

    async def store_agent_result(
    self, 
    verification_id: str, 
    agent_result: Dict[str, Any]
) -> VerificationResult:
        """Store agent verification result"""
        try:
            # Extract fields from agent result
            agent_type = agent_result.get("agent_type")
            status = agent_result.get("status")
            details = agent_result.get("details")
            
            # Store checks separately
            checks = agent_result.get("checks")
            
            # If this is a ResultCompilationAgent, also update the verification's overall result
            if agent_type in ["ResultCompilationAgent", "BusinessResultCompilationAgent"]:
                verification_result = agent_result.get("verification_result")
                reasoning = agent_result.get("reasoning")
                
                if verification_result:
                    # Update the verification record with the final result
                    await self.update_verification_status(
                        verification_id=verification_id,
                        status="completed",
                        result=verification_result,
                        reason=reasoning
                    )
            
            # Create result record
            verification_result = VerificationResult(
                verification_id=verification_id,
                agent_type=agent_type,
                status=status,
                details=details,
                checks=checks
            )
            
            self.session.add(verification_result)
            await self.session.commit()
            await self.session.refresh(verification_result)
            return verification_result
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error storing agent result: {str(e)}")
            raise

    async def get_verification_agent_results(
        self, 
        verification_id: str
    ) -> List[VerificationResult]:
        """Get all agent results for a verification"""
        try:
            result = await self.session.execute(
                select(VerificationResult).where(
                    VerificationResult.verification_id == verification_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting verification agent results: {str(e)}")
            raise

    async def store_ubo_verifications(
        self, 
        verification_id: str, 
        ubo_verifications: List[Dict[str, str]]
    ) -> List[UboVerification]:
        """Store UBO verification references"""
        try:
            ubo_verification_records = []
            
            for ubo_verification in ubo_verifications:
                ubo_user_id = ubo_verification.get("ubo_user_id")
                ubo_verification_id = ubo_verification.get("verification_id")
                
                ubo_verification_record = UboVerification(
                    verification_id=verification_id,
                    ubo_user_id=ubo_user_id,
                    ubo_verification_id=ubo_verification_id
                )
                
                self.session.add(ubo_verification_record)
                ubo_verification_records.append(ubo_verification_record)
            
            await self.session.commit()
            
            # Refresh all records
            for record in ubo_verification_records:
                await self.session.refresh(record)
                
            return ubo_verification_records
        except Exception as e:
            await self.session.rollback()
            self.logger.error(f"Error storing UBO verifications: {str(e)}")
            raise

    async def get_ubo_verifications_for_business(
        self, 
        verification_id: str
    ) -> List[UboVerification]:
        """Get UBO verifications for a business verification"""
        try:
            result = await self.session.execute(
                select(UboVerification).where(
                    UboVerification.verification_id == verification_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            self.logger.error(f"Error getting UBO verifications: {str(e)}")
            raise

    async def get_user_verification_by_user_id(
        self, 
        user_id: str
    ) -> Optional[Verification]:
        """Get most recent user verification by user ID"""
        try:
            result = await self.session.execute(
                select(Verification)
                .where(Verification.user_id == user_id)
                .order_by(Verification.created_at.desc())
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error getting user verification: {str(e)}")
            raise

    async def get_business_verification_by_business_id(
        self, 
        business_id: str
    ) -> Optional[Verification]:
        """Get most recent business verification by business ID"""
        try:
            result = await self.session.execute(
                select(Verification)
                .where(Verification.business_id == business_id)
                .order_by(Verification.created_at.desc())
            )
            return result.scalars().first()
        except Exception as e:
            self.logger.error(f"Error getting business verification: {str(e)}")
            raise

    # New Methods for Listing Verifications
    async def get_verifications(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        verification_type: Optional[str] = None
    ) -> Tuple[List[Verification], int]:
        """
        Get verifications with filtering and pagination
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            verification_type: 'kyc' (user_id is not null) or 'kyb' (business_id is not null)
            
        Returns:
            Tuple of (list of verifications, total count)
        """
        try:
            # Build the base query
            query = select(Verification)
            count_query = select(func.count()).select_from(Verification)
            
            # Apply filters
            if status:
                query = query.where(Verification.status == status)
                count_query = count_query.where(Verification.status == status)
                
            if verification_type == "kyc":
                query = query.where(Verification.user_id.is_not(None))
                count_query = count_query.where(Verification.user_id.is_not(None))
            elif verification_type == "kyb":
                query = query.where(Verification.business_id.is_not(None))
                count_query = count_query.where(Verification.business_id.is_not(None))
            
            # Add pagination and ordering
            query = query.order_by(desc(Verification.created_at)).offset(skip).limit(limit)
            
            # Execute queries
            result = await self.session.execute(query)
            count_result = await self.session.execute(count_query)
            
            verifications = result.scalars().all()
            total_count = count_result.scalar()
            
            return verifications, total_count
        except Exception as e:
            self.logger.error(f"Error getting verifications: {str(e)}")
            raise