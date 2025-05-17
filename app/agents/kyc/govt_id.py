from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class GovtIdVerificationAgent(BaseAgent):
    """Agent for verifying government ID checks in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify government ID checks
        
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
            
            # Define the required checks
            required_checks = [
                {"name": "Barcode Match", "persona_name": "id_barcode_detection"},
                {"name": "Barcode Inconsistency", "persona_name": "id_barcode_inconsistency_detection"},
                {"name": "Compromised submission", "persona_name": "id_compromised_detection"},
                {"name": "Allowed country", "persona_name": "id_disallowed_country_detection"},
                {"name": "Allowed ID type", "persona_name": "id_disallowed_type_detection"},
                {"name": "Electronic replica", "persona_name": "id_electronic_replica_detection"},
                {"name": "Expiration", "persona_name": "id_expired_detection"},
                {"name": "Fabrication", "persona_name": "id_fabrication_detection"},
                {"name": "Inconsistent repeat", "persona_name": "id_inconsistent_repeat_detection"},
                {"name": "Po Box", "persona_name": "id_po_box_detection"},
                {"name": "Portrait clarity", "persona_name": "id_portrait_clarity_detection"},
                {"name": "Portrait", "persona_name": "id_portrait_detection"},
                {"name": "Selfie-to ID comparison", "persona_name": "id_selfie_comparison"},
                {"name": "ID image tampering", "persona_name": "id_tamper_detection"}
            ]
            
            # Process checks
            checks = []
            for required_check in required_checks:
                check_result = next((check for check in govt_id_verification.get("checks", [])
                                    if check.get("name") == required_check["persona_name"]), {})
                
                status = check_result.get("status", "not_applicable")
                metadata = check_result.get("metadata", {})
                
                # Create check result
                checks.append({
                    "name": required_check["name"],
                    "status": status,
                    "details": f"{required_check['name']} check result: {status}",
                    "metadata": metadata
                })
            
            # Use LLM to analyze any suspicious patterns in the ID verification
            risk_analysis = await self.extract_data_with_llm(
                data={"checks": checks},
                prompt="""
                Analyze the following government ID verification checks for suspicious patterns.
                Identify any anomalies or concerning results, even if individual checks passed.
                Your response should include:
                1. An assessment of ID authenticity based on these checks
                2. Any suspicious patterns or potential fraud indicators
                3. A confidence level in the ID verification
                4. Recommendations for additional verification steps if needed
                """
            )
            
            return {
                "agent_type": "GovtIdVerificationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Government ID verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Govt ID verification error: {str(e)}")
            return {
                "agent_type": "GovtIdVerificationAgent",
                "status": "error",
                "details": f"Error during government ID verification: {str(e)}",
                "checks": []
            }