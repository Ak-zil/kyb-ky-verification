from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class IrsMatchAgent(BaseAgent):
    """Agent for verifying IRS (Internal Revenue Service) information in KYB workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify IRS matching
        
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
            
            # 1. EIN/Tax ID Validation
            # Verify that the Tax ID is a valid format
            tax_id_valid = tax_id and len(tax_id.replace("-", "")) == 9 and tax_id.replace("-", "").isdigit()
            
            checks.append({
                "name": "Tax ID Format Validation",
                "status": "passed" if tax_id_valid else "failed",
                "details": f"Tax ID format is {'valid' if tax_id_valid else 'invalid'}: {tax_id}"
            })
            
            # 2. IRS Database Match
            # In a real implementation, this would verify with IRS database
            # For this example, use the mock external data
            tax_id_verified = external_business_data.get("tax_id_verified", False)
            
            checks.append({
                "name": "IRS Database Match",
                "status": "passed" if tax_id_verified else "failed",
                "details": f"Tax ID verified with IRS database: {tax_id_verified}"
            })
            
            # 3. Business Name Match
            # Verify business name matches IRS records
            ein_owner_name = external_business_data.get("ein_owner_name", "")
            name_match = business_name.lower() == ein_owner_name.lower()
            
            checks.append({
                "name": "Business Name Match",
                "status": "passed" if name_match else "failed",
                "details": f"Business name match: {name_match}, Submitted: {business_name}, IRS: {ein_owner_name}"
            })
            
            # 4. Tax Filing Status
            # Verify business is in good standing with IRS
            good_standing = external_business_data.get("good_standing", False)
            
            checks.append({
                "name": "Tax Filing Status",
                "status": "passed" if good_standing else "failed",
                "details": f"Business in good standing with IRS: {good_standing}"
            })
            
            # Use LLM to analyze the IRS verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data,
                    "persona_data": persona_data
                },
                prompt="""
                Analyze the IRS verification results and determine if there are any 
                tax compliance concerns. Consider:
                1. Tax ID validation
                2. IRS database matching
                3. Business name consistency
                4. Tax filing status
                
                Your response should include:
                1. An overall assessment of tax compliance
                2. Any specific compliance concerns or inconsistencies
                3. Recommendations for additional tax verification if needed
                """
            )
            
            return {
                "agent_type": "IrsMatchAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "IRS verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"IRS verification error: {str(e)}")
            return {
                "agent_type": "IrsMatchAgent",
                "status": "error",
                "details": f"Error during IRS verification: {str(e)}",
                "checks": []
            }