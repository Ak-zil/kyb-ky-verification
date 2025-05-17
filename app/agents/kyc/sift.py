from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class SiftVerificationAgent(BaseAgent):
    """Agent for verifying Sift fraud detection checks in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify Sift checks
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            sift_data = verification_data.get("user", {}).get("sift_data", {})
            
            # Process checks
            checks = []
            
            # a. Sift Score
            sift_score = sift_data.get("score", 0)
            sift_score_status = "failed" if sift_score > 70 else "passed"
            checks.append({
                "name": "Sift Score",
                "status": sift_score_status,
                "details": f"Sift score: {sift_score}, {'Above threshold (70)' if sift_score > 70 else 'Below threshold (70)'}"
            })
            
            # b. Sift network
            network_data = sift_data.get("user", {}).get("network", {})
            network_risk_score = network_data.get("risk_score", 0)
            associated_users = network_data.get("associated_users", [])
            
            network_status = "failed" if network_risk_score > 60 or len(associated_users) > 3 else "passed"
            checks.append({
                "name": "Sift network",
                "status": network_status,
                "details": f"Network risk: {network_risk_score}, Associated users: {len(associated_users)}"
            })
            
            # c. Sift Activities
            activities = sift_data.get("user", {}).get("activities", [])
            suspicious_activities = [a for a in activities 
                                    if a.get("status") == "failed" or 
                                    a.get("type") in ["chargeback", "dispute", "refund"]]
            
            activities_status = "failed" if len(suspicious_activities) > 0 else "passed"
            checks.append({
                "name": "Sift Activities",
                "status": activities_status,
                "details": f"Suspicious activities: {len(suspicious_activities)} found"
            })
            
            # Use LLM to analyze patterns in Sift data
            fraud_analysis = await self.extract_data_with_llm(
                data={
                    "sift_score": sift_score,
                    "network_data": network_data,
                    "activities": activities
                },
                prompt="""
                Analyze the following Sift fraud detection data and identify any concerning patterns.
                Look for high-risk indicators in the score, network data, and user activities.
                Your response should include:
                1. An overall fraud risk assessment: 'low', 'medium', or 'high'
                2. Specific suspicious patterns identified, if any
                3. Recommendations for additional fraud prevention measures if needed
                """
            )
            
            return {
                "agent_type": "SiftVerificationAgent",
                "status": "success",
                "details": fraud_analysis.get("summary", "Sift verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Sift verification error: {str(e)}")
            return {
                "agent_type": "SiftVerificationAgent",
                "status": "error",
                "details": f"Error during Sift verification: {str(e)}",
                "checks": []
            }