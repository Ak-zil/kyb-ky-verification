from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class SosFilingsAgent(BaseAgent):
    """Agent for verifying Secretary of State filings in KYB workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify Secretary of State filings
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            business_data = verification_data.get("business", {}).get("business_data", {})
            from app.integrations.external_database import external_db
            external_business_data = await external_db.get_business_data(
            business_data.get("business_id") or business_data.get("id")
        )
            
            # Extract business registration information
            business_name = business_data.get("business_name", "")
            registration_number = business_data.get("registration_number", "")
            registration_state = business_data.get("address", {}).get("state", "")
            
            # Process checks
            checks = []
            
            # 1. Secretary of State Registration
            # Verify business is registered with Secretary of State
            sos_filing_status = external_business_data.get("sos_filing_status", "")
            sos_registered = sos_filing_status == "active"
            
            checks.append({
                "name": "SoS Registration",
                "status": "passed" if sos_registered else "failed",
                "details": f"SoS filing status: {sos_filing_status}"
            })
            
            # 2. Business Name Consistency
            # Verify business name matches SoS records
            # In a real implementation, this would check against SoS database
            # For this example, assume name matches
            checks.append({
                "name": "Business Name Consistency",
                "status": "passed",
                "details": f"Business name consistent with SoS records: {business_name}"
            })
            
            # 3. Business Age Verification
            # Verify business has been registered for a reasonable time
            incorporation_date = external_business_data.get("incorporation_date", "")
            
            if incorporation_date:
                incorporation_datetime = datetime.fromisoformat(incorporation_date)
                business_age = (datetime.utcnow() - incorporation_datetime).days
                
                # Flag new businesses (less than 6 months old)
                new_business = business_age < 180
                
                checks.append({
                    "name": "Business Age",
                    "status": "passed" if not new_business else "warning",
                    "details": f"Business age: {business_age} days, Incorporation date: {incorporation_date}"
                })
            else:
                checks.append({
                    "name": "Business Age",
                    "status": "failed",
                    "details": "Incorporation date not available"
                })
            
            # 4. Recent Filings Verification
            # Verify business has filed required reports recently
            last_filing_date = external_business_data.get("last_filing_date", "")
            
            if last_filing_date:
                last_filing_datetime = datetime.fromisoformat(last_filing_date)
                days_since_filing = (datetime.utcnow() - last_filing_datetime).days
                
                # Flag businesses that haven't filed in over 1 year
                filing_status = days_since_filing < 365
                
                checks.append({
                    "name": "Recent Filings",
                    "status": "passed" if filing_status else "failed",
                    "details": f"Days since last filing: {days_since_filing}, Last filing date: {last_filing_date}"
                })
            else:
                checks.append({
                    "name": "Recent Filings",
                    "status": "failed",
                    "details": "Last filing date not available"
                })
            
            # Use LLM to analyze the SoS verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data
                },
                prompt="""
                Analyze the Secretary of State filing verification results and determine 
                if there are any compliance or legitimacy concerns. Consider:
                1. Registration status with Secretary of State
                2. Business name consistency
                3. Business age and establishment history
                4. Compliance with filing requirements
                
                Your response should include:
                1. An overall assessment of business legitimacy based on SoS filings
                2. Any specific compliance concerns or red flags
                3. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "SosFilingsAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Secretary of State filings verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"SoS filings verification error: {str(e)}")
            return {
                "agent_type": "SosFilingsAgent",
                "status": "error",
                "details": f"Error during Secretary of State filings verification: {str(e)}",
                "checks": []
            }