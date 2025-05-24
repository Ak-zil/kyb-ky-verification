from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.integrations.ofac import ofac_client


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
            
            # Extract user information for OFAC search
            user_info = await self._extract_user_information(user_data, persona_data)
            
            # Process checks
            checks = []
            

            # 1. OFAC API Search
            ofac_search_result = await self._perform_ofac_search(user_info)

  
            
            # 2. Analyze OFAC search results
            ofac_analysis = await ofac_client.analyze_search_results(ofac_search_result)
            
            # 3. Create checks based on results
            checks.extend(await self._create_ofac_checks(ofac_analysis))
            
            # 4. Fallback to Persona watchlist checks if available
            persona_checks = await self._get_persona_watchlist_checks(persona_data)
            checks.extend(persona_checks)
            
            # 5. Country sanctions check
            country_check = await self._check_country_sanctions(user_info.get('country', ''))
            checks.append(country_check)
            
            # Use LLM to analyze the OFAC verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "user_info": user_info,
                    "ofac_analysis": ofac_analysis,
                    "search_results": ofac_search_result
                },
                prompt="""
                Analyze the OFAC sanctions verification results and determine if there 
                are any compliance concerns. Consider:
                1. OFAC API search results and any entity matches
                2. Risk level assessment from the search analysis
                3. Country-based sanctions
                4. Persona watchlist verification results (if available)
                5. Name similarity and address matching confidence
                
                Your response should include:
                1. An overall assessment of sanctions compliance risk (low/medium/high)
                2. Any specific compliance concerns or flags
                3. Details about any matches found and their significance
                4. Recommendations for additional compliance checks if needed
                
                Respond with a JSON object containing:
                - risk_level: "low", "medium", or "high"
                - summary: Brief overall assessment
                - concerns: List of specific concerns
                - recommendations: List of recommended actions
                """
            )
            
            return {
                "agent_type": "OfacVerificationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "OFAC verification completed"),
                "checks": checks,
                "risk_analysis": risk_analysis,
                "ofac_matches": ofac_analysis.get('total_matches', 0)
            }
            
        except Exception as e:
            self.logger.error(f"OFAC verification error: {str(e)}")
            return {
                "agent_type": "OfacVerificationAgent",
                "status": "error",
                "details": f"Error during OFAC verification: {str(e)}",
                "checks": []
            }

    async def _extract_user_information(
        self, 
        user_data: Dict[str, Any], 
        persona_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract user information for OFAC search from various data sources
        
        Args:
            user_data: User data from verification
            persona_data: Persona verification data
            
        Returns:
            Dict containing extracted user information
        """
        try:
            user_info = {
                'name': '',
                'address': '',
                'city': '',
                'state': '',
                'zip': '',
                'country': ''
            }
            
            # Extract name
            user_info['name'] = (
                user_data.get('name', '') or 
                user_data.get('full_name', '') or
                f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            )
            
            # Extract address information
            address_info = user_data.get('address', {})
            if address_info:
                user_info['address'] = address_info.get('street', '') or address_info.get('line1', '')
                user_info['city'] = address_info.get('city', '')
                user_info['state'] = address_info.get('state', '') or address_info.get('subdivision', '')
                user_info['zip'] = address_info.get('postal_code', '') or address_info.get('zip', '')
                user_info['country'] = address_info.get('country', '') or address_info.get('country_code', '')
            
            # Try to extract from Persona data if not found in user_data
            if not user_info['name'] and persona_data:
                persona_attrs = persona_data.get('data', {}).get('attributes', {})
                persona_fields = persona_attrs.get('fields', {})
                
                # Extract name from Persona
                first_name = persona_fields.get('name-first', {}).get('value', '')
                last_name = persona_fields.get('name-last', {}).get('value', '')
                if first_name or last_name:
                    user_info['name'] = f"{first_name} {last_name}".strip()
                
                # Extract address from Persona if not already found
                if not user_info['address']:
                    user_info['address'] = persona_fields.get('address-street-1', {}).get('value', '')
                if not user_info['city']:
                    user_info['city'] = persona_fields.get('address-city', {}).get('value', '')
                if not user_info['state']:
                    user_info['state'] = persona_fields.get('address-subdivision', {}).get('value', '')
                if not user_info['zip']:
                    user_info['zip'] = persona_fields.get('address-postal-code', {}).get('value', '')
                if not user_info['country']:
                    user_info['country'] = persona_fields.get('address-country-code', {}).get('value', '')
            
            # Clean up empty strings
            user_info = {k: v.strip() if isinstance(v, str) else v for k, v in user_info.items()}
            
            self.logger.info(f"Extracted user info for OFAC search: name='{user_info['name']}', country='{user_info['country']}'")
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Error extracting user information: {str(e)}")
            return {
                'name': '',
                'address': '',
                'city': '',
                'state': '',
                'zip': '',
                'country': ''
            }

    async def _perform_ofac_search(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform OFAC search using the extracted user information
        
        Args:
            user_info: Extracted user information
            
        Returns:
            OFAC search results
        """
        try:
            if not user_info.get('name'):
                self.logger.warning("No name available for OFAC search")
                return {'entities': [], 'query': user_info}
            
            search_result = await ofac_client.search_entity(
                name=user_info['name'],
                address=user_info['address'],
                city=user_info['city'],
                state=user_info['state'],
                zip_code=user_info['zip'],
                country=user_info['country']
            )
            
            return search_result
            
        except Exception as e:
            self.logger.error(f"Error performing OFAC search: {str(e)}")
            return {'entities': [], 'query': user_info, 'error': str(e)}

    async def _create_ofac_checks(self, ofac_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create verification checks based on OFAC analysis results
        
        Args:
            ofac_analysis: Analysis results from OFAC search
            
        Returns:
            List of verification checks
        """
        checks = []
        
        # 1. OFAC Match Check
        has_matches = ofac_analysis.get('has_matches', False)
        total_matches = ofac_analysis.get('total_matches', 0)
        risk_level = ofac_analysis.get('risk_level', 'low')
        
        match_status = "failed" if has_matches else "passed"
        
        checks.append({
            "name": "OFAC Sanctions List Match",
            "status": match_status,
            "details": f"OFAC search found {total_matches} potential matches. Risk level: {risk_level}",
            "metadata": {
                "total_matches": total_matches,
                "risk_level": risk_level,
                "sources": ofac_analysis.get('sources', [])
            }
        })
        
        # 2. High Risk Match Check (if there are matches)
        if has_matches:
            high_risk_matches = [
                match for match in ofac_analysis.get('match_details', [])
                if match.get('source', '').lower() in ['sdn', 'ofac', 'specially designated nationals']
            ]
            
            checks.append({
                "name": "High Risk OFAC Match",
                "status": "failed" if high_risk_matches else "passed",
                "details": f"Found {len(high_risk_matches)} high-risk OFAC matches",
                "metadata": {
                    "high_risk_matches": len(high_risk_matches),
                    "match_sources": [m.get('source', '') for m in high_risk_matches]
                }
            })
        
        # 3. Entity Type Analysis
        if has_matches:
            entity_types = [match.get('type', '') for match in ofac_analysis.get('match_details', [])]
            person_matches = sum(1 for t in entity_types if t == 'person')
            business_matches = sum(1 for t in entity_types if t in ['business', 'organization'])
            
            checks.append({
                "name": "OFAC Entity Type Analysis",
                "status": "warning" if person_matches > 0 else "passed",
                "details": f"Person matches: {person_matches}, Business matches: {business_matches}",
                "metadata": {
                    "person_matches": person_matches,
                    "business_matches": business_matches,
                    "entity_types": entity_types
                }
            })
        
        return checks

    async def _get_persona_watchlist_checks(self, persona_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get watchlist checks from Persona data as fallback
        
        Args:
            persona_data: Persona verification data
            
        Returns:
            List of Persona watchlist checks
        """
        checks = []
        
        try:
            # Extract watchlist checks from Persona data
            persona_included = persona_data.get("included", [])
            watchlist_checks = next((item for item in persona_included 
                                    if item.get("type") == "verification/watchlist"), {})
            
            if watchlist_checks:
                # OFAC check from Persona
                ofac_check = next((check for check in watchlist_checks.get("checks", [])
                                 if check.get("name") == "watchlist_ofac_detection"), {})
                
                if ofac_check:
                    ofac_status = ofac_check.get("status", "not_applicable")
                    checks.append({
                        "name": "Persona OFAC Check",
                        "status": ofac_status,
                        "details": f"Persona OFAC watchlist check result: {ofac_status}",
                        "source": "persona"
                    })
                
                # PEP check from Persona
                pep_check = next((check for check in watchlist_checks.get("checks", [])
                                if check.get("name") == "watchlist_pep_detection"), {})
                
                if pep_check:
                    pep_status = pep_check.get("status", "not_applicable")
                    checks.append({
                        "name": "Persona PEP Check",
                        "status": pep_status,
                        "details": f"Persona PEP watchlist check result: {pep_status}",
                        "source": "persona"
                    })
        
        except Exception as e:
            self.logger.error(f"Error extracting Persona watchlist checks: {str(e)}")
        
        return checks

    async def _check_country_sanctions(self, country: str) -> Dict[str, Any]:
        """
        Check if the user's country is under sanctions
        
        Args:
            country: Country code or name
            
        Returns:
            Country sanctions check result
        """
        # List of sanctioned countries (this could be made configurable)
        sanctioned_countries = [
            "North Korea", "Iran", "Syria", "Cuba", "Russia", "Belarus",
            "KP", "IR", "SY", "CU", "RU", "BY"  # Country codes
        ]
        
        country_sanctioned = country.upper() in [c.upper() for c in sanctioned_countries]
        
        return {
            "name": "Country Sanctions Check",
            "status": "failed" if country_sanctioned else "passed",
            "details": f"Country: {country}, Sanctioned: {country_sanctioned}",
            "metadata": {
                "country": country,
                "is_sanctioned": country_sanctioned
            }
        }