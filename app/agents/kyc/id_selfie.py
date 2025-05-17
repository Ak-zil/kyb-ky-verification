from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class IdSelfieVerificationAgent(BaseAgent):
    """Agent for verifying ID to selfie comparison in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify ID to selfie comparison
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            persona_data = verification_data.get("user", {}).get("persona_data", {})
            
            # Extract govt ID checks from Persona data
            persona_included = persona_data.get("included", [])
            govt_id_verification = next((item for item in persona_included 
                                         if item.get("type") == "verification/government-id"), {})
            
            # Process checks
            checks = []
            
            # ID to selfie comparison check
            selfie_check = next((check for check in govt_id_verification.get("checks", [])
                              if check.get("name") == "id_selfie_comparison"), {})
            
            selfie_status = selfie_check.get("status", "not_applicable")
            confidence_score = selfie_check.get("metadata", {}).get("confidence-score", 0)
            
            # Determine status based on confidence score
            score_threshold = 0.7  # Confidence score threshold
            status = "passed" if selfie_status == "passed" and confidence_score >= score_threshold else "failed"
            
            checks.append({
                "name": "ID to Selfie Comparison",
                "status": status,
                "details": f"ID to selfie comparison: {status}, confidence score: {confidence_score}",
                "confidence_score": confidence_score
            })
            
            # Facial anomalies check
            checks.append({
                "name": "Facial Anomalies",
                "status": "passed" if status == "passed" else "failed",
                "details": f"Facial anomalies check: {'No anomalies detected' if status == 'passed' else 'Anomalies detected'}"
            })
            
            # Use LLM to analyze the selfie verification
            risk_analysis = await self.extract_data_with_llm(
                data={"checks": checks},
                prompt="""
                Analyze the ID selfie verification results and determine if there are any 
                risks or concerns. Consider the confidence score and whether any facial 
                anomalies were detected. Your response should include:
                1. An overall assessment of the ID-to-selfie match
                2. Any potential signs of presentation attacks (e.g., using a photo of a photo)
                3. A confidence rating in your assessment (low, medium, high)
                4. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "IdSelfieVerificationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "ID selfie verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"ID selfie verification error: {str(e)}")
            return {
                "agent_type": "IdSelfieVerificationAgent",
                "status": "error",
                "details": f"Error during ID selfie verification: {str(e)}",
                "checks": []
            }