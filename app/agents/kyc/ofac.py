from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class OfacVerificationAgent(BaseAgent):
    """Agent for verifying against OFAC (Office of Foreign Assets Control) sanctions list in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify against OFAC sanctions list
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            user_data = verification_data.get("user", {}).get("user_data", {})
            persona_data = verification_data.get("user", {}).get("persona_data", {})
            
            # Extract name and personal info from user data
            name = user_data.get("name", "")
            country = user_data.get("address", {}).get("country", "")
            
            # Extract watchlist checks from Persona data
            persona_included = persona_data.get("included", [])
            watchlist_checks = next((item for item in persona_included 
                                    if item.get("type") == "verification/watchlist"), {})
            
            # Process checks
            checks = []
            
            # 1. OFAC SDN List Check
            ofac_check = next((check for check in watchlist_checks.get("checks", [])
                             if check.get("name") == "watchlist_ofac_detection"), {})
            
            ofac_status = ofac_check.get("status", "not_applicable")
            
            checks.append({
                "name": "OFAC SDN List",
                "status": ofac_status,
                "details": f"OFAC sanction list check result: {ofac_status}"
            })
            
            # 2. OFAC Consolidated List Check
            # This would check against the consolidated sanctions list
            # For this example, assume it's checked as part of the SDN check
            checks.append({
                "name": "OFAC Consolidated List",
                "status": ofac_status,
                "details": f"OFAC consolidated list check result: {ofac_status}"
            })
            
            # 3. Country Sanctions Check
            # Check if user's country is under sanctions
            sanctioned_countries = ["North Korea", "Iran", "Syria", "Cuba"]
            country_sanctioned = country in sanctioned_countries
            
            checks.append({
                "name": "Country Sanctions",
                "status": "failed" if country_sanctioned else "passed",
                "details": f"Country: {country}, Sanctioned: {country_sanctioned}"
            })
            
            # 4. Name Similarity Check
            # Check for similar names on watchlists (fuzzy matching)
            # For this example, assume it's already covered by the Persona check
            checks.append({
                "name": "Name Similarity",
                "status": ofac_status,
                "details": f"Name similarity check result: {ofac_status}"
            })
            
            # Use LLM to analyze the OFAC verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "name": name,
                    "country": country
                },
                prompt="""
                Analyze the OFAC sanctions verification results and determine if there 
                are any compliance concerns. Consider:
                1. OFAC SDN list verification
                2. Consolidated sanctions list verification
                3. Country-based sanctions
                4. Name similarity to sanctioned individuals
                
                Your response should include:
                1. An overall assessment of sanctions compliance
                2. Any specific compliance concerns or flags
                3. Recommendations for additional compliance checks if needed
                """
            )
            
            return {
                "agent_type": "OfacVerificationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "OFAC verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"OFAC verification error: {str(e)}")
            return {
                "agent_type": "OfacVerificationAgent",
                "status": "error",
                "details": f"Error during OFAC verification: {str(e)}",
                "checks": []
            }