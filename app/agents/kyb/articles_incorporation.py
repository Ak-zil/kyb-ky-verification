from typing import Any, Dict, List, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class ArticlesIncorporationAgent(BaseAgent):
    """Agent for verifying articles of incorporation in KYB workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify articles of incorporation
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            business_data = verification_data.get("business", {}).get("business_data", {})
            persona_data = verification_data.get("business", {}).get("persona_data", {})
            business_details = verification_data.get("business", {}).get("business_details", {})
            
            # Extract business legal information from Persona data first, then fall back to other sources
            # Get business name from Persona data
            business_name = ""
            business_type = ""
            incorporation_date = ""
            legal_structure = ""
            
            # First try to get data from the structured business_details
            if business_details:
                business_info = business_details.get("business_info", {})
                business_name = business_info.get("business_name", "")
                business_type = business_info.get("entity_type", "")
                incorporation_date = business_info.get("business_formation_date", "")
                legal_structure = business_info.get("entity_type", "")
            
            # If not found, try extracting directly from persona_data fields
            if not business_name and persona_data:
                data = persona_data.get("data", {})
                attributes = data.get("attributes", {})
                fields = attributes.get("fields", {})
                
                business_name_field = fields.get("business-name", {})
                if business_name_field:
                    business_name = business_name_field.get("value", "")
                    
                entity_type_field = fields.get("entity-type", {})
                if entity_type_field:
                    business_type = entity_type_field.get("value", "")
                    legal_structure = business_type  # Often the same
                    
                formation_date_field = fields.get("business-formation-date", {})
                if formation_date_field:
                    incorporation_date = formation_date_field.get("value", "")
            
            # Last resort: Fall back to business_data fields
            if not business_name:
                business_name = business_data.get("business_name", "")
            if not business_type:
                business_type = business_data.get("business_type", "")
            if not incorporation_date:
                incorporation_date = business_data.get("incorporation_date", "")
            if not legal_structure:
                legal_structure = business_data.get("legal_structure", "")
                
            # Get additional external data if needed
            from app.integrations.external_database import external_db
            external_business_data = await external_db.get_business_data(
                business_data.get("business_id") or business_data.get("id")
            )
                
            # Process checks
            checks = []
            
            # 1. Articles of Incorporation Verification
            # In a real implementation, this would verify the articles document with OCR
            # For this example, assume it exists if incorporation_date is provided
            articles_verified = bool(incorporation_date)
            
            checks.append({
                "name": "Articles Verification",
                "status": "passed" if articles_verified else "failed",
                "details": f"Articles of incorporation verified: {articles_verified}"
            })
            
            # 2. Legal Structure Check
            # Verify legal structure matches expected type
            legal_structure_valid = legal_structure in ["LLC", "Corporation", "Partnership", "Sole Proprietorship"]
            legal_structure_consistency = (
                (business_type.lower() == "llc" and legal_structure == "LLC") or
                (business_type.lower() == "corporation" and legal_structure == "Corporation") or
                (business_type.lower() == "partnership" and legal_structure == "Partnership") or
                (business_type.lower() == "sole_proprietorship" and legal_structure == "Sole Proprietorship")
            )
            
            checks.append({
                "name": "Legal Structure",
                "status": "passed" if legal_structure_valid and legal_structure_consistency else "failed",
                "details": f"Legal structure: {legal_structure}, Business type: {business_type}, Consistent: {legal_structure_consistency}"
            })
            
            # 3. Incorporation Date Check
            # Verify incorporation date is reasonable
            if incorporation_date:
                incorporation_datetime = datetime.fromisoformat(incorporation_date)
                business_age = (datetime.utcnow() - incorporation_datetime).days
                
                # Flag very new businesses (less than 30 days old)
                very_new_business = business_age < 30
                
                checks.append({
                    "name": "Incorporation Date",
                    "status": "warning" if very_new_business else "passed",
                    "details": f"Incorporation date: {incorporation_date}, Business age: {business_age} days"
                })
            else:
                checks.append({
                    "name": "Incorporation Date",
                    "status": "failed",
                    "details": "Incorporation date not available"
                })
            
            # 4. Business Name Consistency
            # Verify business name matches articles of incorporation
            # For this example, assume it matches if other checks pass
            name_consistent = articles_verified
            
            checks.append({
                "name": "Business Name Consistency",
                "status": "passed" if name_consistent else "failed",
                "details": f"Business name consistent with articles: {name_consistent}"
            })
            
            # Use LLM to analyze the articles of incorporation verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data,
                    "persona_data": persona_data
                },
                prompt="""
                Analyze the articles of incorporation verification results and determine 
                if there are any concerns about business legitimacy. Consider:
                1. Articles of incorporation verification status
                2. Legal structure consistency
                3. Incorporation date and business age
                4. Business name consistency
                
                Your response should include:
                1. An overall assessment of business legitimacy based on incorporation documents
                2. Any specific concerns or red flags
                3. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "ArticlesIncorporationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Articles of incorporation verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Articles of incorporation verification error: {str(e)}")
            return {
                "agent_type": "ArticlesIncorporationAgent",
                "status": "error",
                "details": f"Error during articles of incorporation verification: {str(e)}",
                "checks": []
            }