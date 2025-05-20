from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class EinLetterAgent(BaseAgent):
    """Agent for verifying EIN (Employer Identification Number) letter in KYB workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify EIN letter
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            business_data = verification_data.get("business", {}).get("business_data", {})
            persona_data = verification_data.get("business", {}).get("persona_data", {})
            business_details = verification_data.get("business", {}).get("business_details", {})
            
            # Extract business information from Persona data first, then fall back to other sources
            business_name = ""
            tax_id = ""
            
            # First try to get data from the structured business_details
            if business_details:
                business_info = business_details.get("business_info", {})
                business_name = business_info.get("business_name", "")
                tax_id = business_info.get("business_tax_id", "")
            
            # If not found, try extracting directly from persona_data fields
            if not business_name and persona_data:
                data = persona_data.get("data", {})
                attributes = data.get("attributes", {})
                fields = attributes.get("fields", {})
                
                business_name_field = fields.get("business-name", {})
                if business_name_field:
                    business_name = business_name_field.get("value", "")
                    
                tax_id_field = fields.get("business-tax-identification-number", {})
                if tax_id_field:
                    tax_id = tax_id_field.get("value", "")
            
            # Last resort: Fall back to business_data fields
            if not business_name:
                business_name = business_data.get("business_name", "")
            if not tax_id:
                tax_id = business_data.get("tax_id", "")
                
            # Get additional external data if needed
            from app.integrations.external_database import external_db
            external_business_data = await external_db.get_business_data(
                business_data.get("business_id") or business_data.get("id")
            )
                
            # Process checks
            checks = []
            
            # 1. EIN Letter Verification
            # In a real implementation, this would verify the EIN letter with OCR
            # For this example, use the mock external data
            ein_letter_verified = external_business_data.get("ein_letter_verified", False)
            
            checks.append({
                "name": "EIN Letter Verification",
                "status": "passed" if ein_letter_verified else "failed",
                "details": f"EIN letter verified: {ein_letter_verified}"
            })
            
            # 2. EIN Number Format Check
            # Verify EIN format is valid (9 digits, typically XX-XXXXXXX)
            ein_format_valid = tax_id and len(tax_id.replace("-", "")) == 9 and tax_id.replace("-", "").isdigit()
            
            checks.append({
                "name": "EIN Format Check",
                "status": "passed" if ein_format_valid else "failed",
                "details": f"EIN format valid: {ein_format_valid}, EIN: {tax_id}"
            })
            
            # 3. Business Name Match
            # Verify business name on EIN letter matches business name
            ein_owner_name = external_business_data.get("ein_owner_name", "")
            name_match = business_name.lower() == ein_owner_name.lower()
            
            checks.append({
                "name": "Business Name Match",
                "status": "passed" if name_match else "failed",
                "details": f"Business name match: {name_match}, Submitted: {business_name}, EIN letter: {ein_owner_name}"
            })
            
            # 4. Letter Authenticity Check
            # In a real implementation, this would check for IRS letter authenticity markers
            # For this example, assume it's part of the ein_letter_verified check
            checks.append({
                "name": "Letter Authenticity",
                "status": "passed" if ein_letter_verified else "failed",
                "details": f"Letter authenticity verified: {ein_letter_verified}"
            })
            
            # Use LLM to analyze the EIN letter verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data,
                    "persona_data": persona_data
                },
                prompt="""
                Analyze the EIN letter verification results and determine if there are any 
                concerns about its authenticity. Consider:
                1. EIN letter verification status
                2. EIN number format validity
                3. Business name consistency
                4. Letter authenticity indicators
                
                Your response should include:
                1. An overall assessment of the EIN letter authenticity
                2. Any specific concerns or inconsistencies
                3. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "EinLetterAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "EIN letter verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"EIN letter verification error: {str(e)}")
            return {
                "agent_type": "EinLetterAgent",
                "status": "error",
                "details": f"Error during EIN letter verification: {str(e)}",
                "checks": []
            }