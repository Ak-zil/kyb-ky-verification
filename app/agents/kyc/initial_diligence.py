from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class InitialDiligenceAgent(BaseAgent):
    """Agent for performing initial diligence checks in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify initial diligence checks
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            
            # Extract user data
            user_data = verification_data.get("user", {}).get("user_data", {})
            persona_data = verification_data.get("user", {}).get("persona_data", {})
            
            # Extract PEP and OFAC checks from Persona data
            persona_included = persona_data.get("included", [])
            watchlist_checks = next((item for item in persona_included 
                                    if item.get("type") == "verification/watchlist"), {})
            
            # Process checks
            checks = []
            
            # a. Identity Verification (Database)
            identity_verified = user_data.get("identity_verified", False)
            checks.append({
                "name": "Identity Verification",
                "status": "passed" if identity_verified else "failed",
                "details": "Identity verified in database" if identity_verified else "Identity not verified"
            })
            
            # b. Watchlist (PEP)
            pep_check = next((check for check in watchlist_checks.get("checks", [])
                             if check.get("name") == "watchlist_pep_detection"), {})
            pep_status = pep_check.get("status", "not_applicable")
            checks.append({
                "name": "Watchlist (PEP)",
                "status": pep_status,
                "details": f"PEP check result: {pep_status}"
            })
            
            # c. Watchlist (OFAC)
            ofac_check = next((check for check in watchlist_checks.get("checks", [])
                              if check.get("name") == "watchlist_ofac_detection"), {})
            ofac_status = ofac_check.get("status", "not_applicable")
            checks.append({
                "name": "Watchlist (OFAC)",
                "status": ofac_status,
                "details": f"OFAC check result: {ofac_status}"
            })
            
            # d. Banned Geographies
            geo_check = next((check for check in persona_included if check.get("type") == "verification/geolocation"), {})
            geo_status = geo_check.get("status", "not_applicable")
            checks.append({
                "name": "Banned Geographies",
                "status": geo_status,
                "details": f"Geography check result: {geo_status}"
            })
            
            # Use LLM to analyze overall risk from these checks
            risk_analysis = await self.extract_data_with_llm(
                data={"checks": checks},
                prompt="""
                Analyze the following identity verification checks and determine the overall risk level.
                Consider each check's status and provide a brief explanation of your assessment.
                Your response should include:
                1. An overall risk level: 'low', 'medium', or 'high'
                2. A summary explanation of why you assigned this risk level
                3. Any recommendations for additional verification steps if needed
                """
            )
            
            return {
                "agent_type": "InitialDiligenceAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Initial diligence checks completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Initial diligence error: {str(e)}")
            return {
                "agent_type": "InitialDiligenceAgent",
                "status": "error",
                "details": f"Error during initial diligence verification: {str(e)}",
                "checks": []
            }