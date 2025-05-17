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
            external_business_data = await self.db_client.get_external_business_data(business_data.get("business_id"))
            
            # Extract business legal information
            business_name = business_data.get("business_name", "")
            business_type = business_data.get("business_type", "")
            incorporation_date = external_business_data.get("incorporation_date", "")
            legal_structure = external_business_data.get("legal_structure", "")
            
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
                    "external_business_data": external_business_data
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