from typing import Any, Dict, Optional

from app.agents.base import BaseAgent
from app.integrations.database import Database
from app.integrations.external_database import external_db
from app.integrations.persona import PersonaClient
from app.integrations.sift import SiftClient
from app.utils.json_encoder import convert_dates_to_strings
from app.utils.llm import BedrockClient
from app.utils.logging import get_logger


class DataAcquisitionAgent(BaseAgent):
    """Agent for acquiring data from various sources"""

    def __init__(
        self,
        verification_id: str,
        business_id: Optional[str] = None,
        user_id: Optional[str] = None,
        bedrock_client: Optional[BedrockClient] = None,
        db_client: Optional[Database] = None,
        persona_client: Optional[PersonaClient] = None,
        sift_client: Optional[SiftClient] = None,
    ):
        """
        Initialize data acquisition agent
        
        Args:
            verification_id: ID of the verification
            business_id: ID of the business (for KYB)
            user_id: ID of the user (for KYC)
            bedrock_client: Amazon Bedrock client
            db_client: Database client
            persona_client: Persona client
            sift_client: Sift client
        """
        super().__init__(
            verification_id=verification_id,
            bedrock_client=bedrock_client,
            db_client=db_client,
            persona_client=persona_client,
            sift_client=sift_client,
        )
        self.business_id = business_id
        self.user_id = user_id

    async def run(self) -> Dict[str, Any]:
        """
        Acquire data from various sources
        
        Returns:
            Dict containing acquired data
        """
        try:
            result = {
                "agent_type": "DataAcquisitionAgent",
                "status": "success",
                "details": "Successfully acquired data from all sources",
                "data": {}
            }
            
            # For KYC workflow - user data
            if self.user_id:
                await self._acquire_user_data(result)
                
            # For KYB workflow - business data and UBOs
            if self.business_id:
                await self._acquire_business_data(result)
                
            # Store the acquired data in the database
            for data_type, data in result["data"].items():
                await self.db_client.store_verification_data(
                    verification_id=self.verification_id,
                    data_type=data_type,
                    data=data
                )
                
            return result
            
        except Exception as e:
            self.logger.error(f"Data acquisition error: {str(e)}")
            return {
                "agent_type": "DataAcquisitionAgent",
                "status": "error",
                "details": f"Error during data acquisition: {str(e)}",
                "data": {}
            }

    async def _acquire_user_data(self, result: Dict[str, Any]) -> None:
        """
        Acquire user data for KYC verification
        
        Args:
            result: Result dictionary to update
        """
        try:
            # Fetch Persona inquiry ID from external database
            persona_enquiry_id = await external_db.get_persona_inquiry_id(self.user_id)
            self.logger.info(f"Persona inquiry ID for user {self.user_id}: {persona_enquiry_id}")
            

            
            # Fetch Sift scores from external database
            sift_data = await external_db.get_sift_scores(self.user_id)
            self.logger.info(f"Sift data fetched for user {self.user_id}")
            
            # Fetch Persona data if inquiry ID is available
            persona_data = {}
            if persona_enquiry_id:
                persona_data = await self.persona_client.get_inquiry(persona_enquiry_id)
                self.logger.info(f"Persona data fetched for inquiry ID {persona_enquiry_id}")
                
            # Create user data structure with all information
            user_data = {
                "user_id": self.user_id,
                "persona_enquiry_id": persona_enquiry_id
            }
            
            # Store data in result
            result["data"]["user"] = {
                "user_data": user_data,
                "persona_data": persona_data,
                "sift_data": sift_data or {}
            }
        except Exception as e:
            self.logger.error(f"Error acquiring user data: {str(e)}")
            # Still create basic user data even if error occurs
            result["data"]["user"] = {
                "user_data": {"user_id": self.user_id},
                "persona_data": {},
                "sift_data": {}
            }

    async def _acquire_business_data(self, result: Dict[str, Any]) -> None:
        """
        Acquire business data for KYB verification
        
        Args:
            result: Result dictionary to update
        """
        try:
            # 1. Fetch business data from external database using business_id as id
            user_kyb_record = await external_db.get_business_data(self.business_id)
            if not user_kyb_record:
                self.logger.warning(f"Business data not found for ID {self.business_id}")
                # Create minimal business data
                business_data = {"business_id": self.business_id}
                result["data"]["business"] = {
                    "business_data": business_data,
                    "ubos": []
                }
                return
            
            # 2. Get the user_id from the fetched business data
            user_id = user_kyb_record.get("user_id")
            if not user_id:
                self.logger.warning(f"User ID not found in business record for business {self.business_id}")
                business_data = {"business_id": self.business_id}
                result["data"]["business"] = {
                    "business_data": business_data,
                    "ubos": []
                }
                return
            
            # 3. Fetch the Persona inquiry ID for KYB
            persona_inquiry_id = await external_db.get_persona_inquiry_id(user_id, "kyb")
            self.logger.info(f"Persona KYB inquiry ID for user {user_id}: {persona_inquiry_id}")
            
            # 4. Get business data from Persona
            business_details = {}
            if persona_inquiry_id:
                # Fetch the inquiry data from Persona
                persona_data = await self.persona_client.get_inquiry(persona_inquiry_id)
                self.logger.info(f"Persona data fetched for KYB inquiry ID {persona_inquiry_id}")
                
                # Extract business details from Persona inquiry
                business_details = await self.persona_client.extract_business_info(persona_data)
                self.logger.info("Business details extracted from Persona inquiry")
                
            # 5. Combine data from user_kyb_record and Persona
            business_data = {
                "business_id": self.business_id,
                "user_id": user_id,
                "persona_inquiry_id": persona_inquiry_id,
                **user_kyb_record,
                **business_details.get("business_info", {})
            }
            
            # 6. Fetch UBO data from external database
            ubos = await external_db.get_business_owners(self.business_id)
            self.logger.info(f"Found {len(ubos)} UBOs for business {self.business_id}")
            
            # 7. For each UBO, fetch KYC data
            ubo_data = []
            for ubo in ubos:
                ubo_user_id = ubo.get("created_for_id") # TODO: user_id
                if not ubo_user_id:
                    self.logger.warning("UBO user ID not found in UBO record")
                    continue
                    
                # Get Persona inquiry ID for UBO (KYC)
                owner_inquiry_id = await external_db.get_persona_inquiry_id(ubo_user_id, "kyc")
                
                # Get Sift scores for UBO
                ubo_sift_data = await external_db.get_sift_scores(ubo_user_id)
                
                # Get Persona data if inquiry ID is available
                ubo_persona_data = {}
                if owner_inquiry_id:
                    ubo_persona_data = await self.persona_client.get_inquiry(owner_inquiry_id)
                
                # Create UBO data structure
                ubo_data.append({
                    "ubo_info": ubo,
                    "kyc_data": {
                        "user_data": {
                            "user_id": ubo_user_id,
                            "persona_inquiry_id": owner_inquiry_id
                        },
                        "persona_data": ubo_persona_data,
                        "sift_data": ubo_sift_data or {}
                    }
                })
            
            # 8. Store data in result
            result["data"]["business"] = {
                "business_data": business_data,
                "persona_data": persona_data if 'persona_data' in locals() else {},
                "ubos": ubo_data
            }
            
            # Convert dates to strings for JSON serialization
            result["data"] = convert_dates_to_strings(result["data"])
            
        except Exception as e:
            self.logger.error(f"Error acquiring business data: {str(e)}")
            # Still create basic business data even if error occurs
            result["data"]["business"] = {
                "business_data": {"business_id": self.business_id},
                "ubos": []
            }



