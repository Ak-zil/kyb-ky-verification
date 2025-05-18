from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class NormalDiligenceAgent(BaseAgent):
    """Agent for performing normal diligence checks in KYB workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify normal diligence checks for business
        
        Returns:
            Dict containing verification results
        """
        try:


            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()




            business_data = verification_data.get("business", {}).get("business_data", {})

            
            # Get business type and industry data
            business_type = business_data.get("business_type", "")
            industry_type = business_data.get("industry_type", "")
            
            # Get external data
            from app.integrations.external_database import external_db



            external_business_data = await external_db.get_business_data(
                business_data.get("business_id") or business_data.get("id")
            )

            
            # Get open corporates data
            open_corporates_data = await self.sift_client.get_open_corporates_data(
                business_data.get("business_name", ""), 
                business_data.get("registration_country", "")
            )
            
            # Process checks
            checks = []
            
            # a. Business Type
            banned_business_types = ["gambling", "cryptocurrency_exchange", "adult_content", "weapons"]
            business_type_status = "failed" if business_type.lower() in banned_business_types else "passed"
            
            # Cross-validate with open corporates
            oc_business_type = open_corporates_data.get("business_type", "")
            business_type_match = business_type.lower() == oc_business_type.lower()
            
            checks.append({
                "name": "Business Type",
                "status": business_type_status,
                "details": f"Business type: {business_type}, {'Banned type' if business_type_status == 'failed' else 'Allowed type'}, Match with external data: {business_type_match}"
            })
            
            # b. Industry Type
            banned_industries = ["gambling", "adult_entertainment", "weapons_manufacturing", "cryptocurrency"]
            industry_status = "failed" if industry_type.lower() in banned_industries else "passed"
            
            # Cross-validate with open corporates
            oc_industry = open_corporates_data.get("industry", "")
            industry_match = industry_type.lower() == oc_industry.lower()
            
            checks.append({
                "name": "Industry Type",
                "status": industry_status,
                "details": f"Industry type: {industry_type}, {'Banned industry' if industry_status == 'failed' else 'Allowed industry'}, Match with external data: {industry_match}"
            })
            
            # c. KYC/UBO Information
            ubo_name = business_data.get("ubo_name", "")
            ein_owner_name = external_business_data.get("ein_owner_name", "")
            
            ubo_match = ubo_name.lower() == ein_owner_name.lower()
            ubo_status = "passed" if ubo_match else "failed"
            
            checks.append({
                "name": "KYC/UBO Information",
                "status": ubo_status,
                "details": f"UBO name: {ubo_name}, EIN owner name: {ein_owner_name}, Match: {ubo_match}"
            })
            
            # d. Banned Geographics
            banned_countries = ["North Korea", "Iran", "Syria", "Cuba"]
            business_country = business_data.get("address", {}).get("country", "")
            
            geography_status = "failed" if business_country in banned_countries else "passed"
            
            checks.append({
                "name": "Banned Geographics",
                "status": geography_status,
                "details": f"Business country: {business_country}, {'Banned country' if geography_status == 'failed' else 'Allowed country'}"
            })
            
            # Use LLM to analyze overall risk from these checks
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "business_data": business_data,
                    "external_data": external_business_data,
                    "open_corporates_data": open_corporates_data,
                    "checks": checks
                },
                prompt="""
                Analyze the following business verification checks and determine if there are any inconsistencies
                or red flags between the provided business data and external sources.
                Your response should include:
                1. An overall assessment of business legitimacy
                2. Any inconsistencies or discrepancies between data sources
                3. Potential risk factors identified
                4. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "NormalDiligenceAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Normal diligence checks completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Normal diligence error: {str(e)}")
            return {
                "agent_type": "NormalDiligenceAgent",
                "status": "error",
                "details": f"Error during normal diligence verification: {str(e)}",
                "checks": []
            }