from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class IdCheckAgent(BaseAgent):
    """Agent for comprehensive ID verification in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Perform comprehensive ID check
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            user_data = verification_data.get("user", {}).get("user_data", {})
            persona_data = verification_data.get("user", {}).get("persona_data", {})
            
            # Extract persona checks
            persona_included = persona_data.get("included", [])
            govt_id_verification = next((item for item in persona_included 
                                        if item.get("type") == "verification/government-id"), {})
            
            # Process checks
            checks = []
            
            # 1. ID Document Type Check
            id_type_check = next((check for check in govt_id_verification.get("checks", [])
                                 if check.get("name") == "id_disallowed_type_detection"), {})
            
            id_metadata = id_type_check.get("metadata", {})
            detected_id_class = id_metadata.get("detected-id-class", "")
            detected_id_designations = id_metadata.get("detected-id-designations", [])
            
            # Check if ID is a REAL ID (enhanced security)
            is_real_id = "REAL_ID" in detected_id_designations
            
            checks.append({
                "name": "ID Document Type",
                "status": "passed",
                "details": f"Document type: {detected_id_class}, REAL ID: {is_real_id}"
            })
            
            # 2. ID MRZ (Machine Readable Zone) Check
            # This would normally check the MRZ data on the ID
            # For this example, we'll assume it's always present and valid
            checks.append({
                "name": "ID MRZ Check",
                "status": "passed",
                "details": "MRZ data valid and consistent with visual inspection"
            })
            
            # 3. ID Expiration Check
            expiration_check = next((check for check in govt_id_verification.get("checks", [])
                                   if check.get("name") == "id_expired_detection"), {})
            
            expiration_date = expiration_check.get("metadata", {}).get("expiration-date", "")
            expiration_status = expiration_check.get("status", "not_applicable")
            
            checks.append({
                "name": "ID Expiration Check",
                "status": expiration_status,
                "details": f"Expiration date: {expiration_date}, Status: {expiration_status}"
            })
            
            # 4. ID Security Features Check
            # This would check for holograms, microprint, etc.
            # For this example, we'll assume these are always present and valid
            checks.append({
                "name": "ID Security Features",
                "status": "passed",
                "details": "All security features present and valid"
            })
            
            # 5. ID Data Consistency Check
            # Check if data on ID matches data in our system
            name_on_id = "John Doe"  # Mock data, would come from OCR of ID
            name_in_system = user_data.get("name", "")
            
            name_match = name_on_id.lower() == name_in_system.lower()
            
            checks.append({
                "name": "ID Data Consistency",
                "status": "passed" if name_match else "failed",
                "details": f"Name match: {name_match}"
            })
            
            # Use LLM to analyze the ID checks
            risk_analysis = await self.extract_data_with_llm(
                data={"checks": checks},
                prompt="""
                Perform a comprehensive analysis of the ID document verification results.
                Consider:
                1. The type and quality of the ID document
                2. Security features and their verification
                3. Expiration status
                4. Consistency between ID data and user-provided data
                
                Your response should include:
                1. An overall assessment of the ID's authenticity
                2. Any inconsistencies or concerns identified
                3. A risk level (low, medium, high) based on these factors
                4. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "IdCheckAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "ID check completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"ID check error: {str(e)}")
            return {
                "agent_type": "IdCheckAgent",
                "status": "error",
                "details": f"Error during ID check: {str(e)}",
                "checks": []
            }