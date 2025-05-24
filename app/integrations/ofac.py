import asyncio
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("ofac")


class OfacClient:
    """
    Client for OFAC sanctions verification API
    
    This client handles communication with the external OFAC API service
    for sanctions list verification.
    """

    def __init__(self, base_url: Optional[str] = None):
        """Initialize OFAC client"""
        self.base_url = base_url or "http://3.101.52.222:8084"
        self.search_endpoint = f"{self.base_url}/search"
        self.logger = logger
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def search_entity(
        self, 
        name: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for an entity in OFAC sanctions lists
        
        Args:
            name: Entity name to search
            address: Street address
            city: City
            state: State/Province
            zip_code: ZIP/Postal code
            country: Country
            
        Returns:
            Dict containing search results
        """
        try:
            # Prepare query parameters
            params = {
                'name': name or '',
                'address': address or '',
                'city': city or '',
                'state': state or '',
                'zip': zip_code or '',
                'country': country or '',
            }
            
            # Remove empty parameters
            params = {k: v for k, v in params.items() if v}
            
            self.logger.info(f"Searching OFAC for entity: {name}")
            self.logger.debug(f"OFAC search parameters: {params}")
            
            response = await self.http_client.get(
                self.search_endpoint, 
                params=params
            )
            response.raise_for_status()
            
            result = response.json()
            
            self.logger.info(f"OFAC search completed for {name}, found {len(result.get('entities', []))} entities")
            
            return result
            
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error during OFAC search: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error during OFAC search: {str(e)}")
            raise

    async def analyze_search_results(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze OFAC search results and extract key information
        
        Args:
            search_results: Raw search results from OFAC API
            
        Returns:
            Dict containing analysis results
        """
        try:
            entities = search_results.get('entities', [])
            query_info = search_results.get('query', {})
            
            analysis = {
                'total_matches': len(entities),
                'has_matches': len(entities) > 0,
                'query_info': query_info,
                'match_details': [],
                'risk_level': 'low',
                'sources': set()
            }
            
            # Analyze each entity match
            for entity in entities:
                entity_analysis = {
                    'name': entity.get('name', ''),
                    'type': entity.get('type', ''),
                    'source': entity.get('source', ''),
                    'source_id': entity.get('sourceID', ''),
                    'addresses': entity.get('addresses', []),
                    'person_info': entity.get('person', {}),
                    'business_info': entity.get('business', {}),
                    'organization_info': entity.get('organization', {})
                }
                
                analysis['match_details'].append(entity_analysis)
                
                # Track sources
                if entity.get('source'):
                    analysis['sources'].add(entity.get('source'))
            
            # Determine risk level based on matches
            if analysis['has_matches']:
                # Check for exact name matches or high-confidence matches
                exact_matches = [
                    entity for entity in entities 
                    if entity.get('name', '').lower() == query_info.get('name', '').lower()
                ]
                
                if exact_matches:
                    analysis['risk_level'] = 'high'
                elif len(entities) > 0:
                    analysis['risk_level'] = 'medium'
            
            # Convert sources set to list for JSON serialization
            analysis['sources'] = list(analysis['sources'])
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing OFAC search results: {str(e)}")
            raise

    async def batch_search_entities(
        self, 
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Perform batch search for multiple entities
        
        Args:
            entities: List of entity dictionaries with search parameters
            
        Returns:
            List of search results for each entity
        """
        try:
            search_tasks = []
            
            for entity in entities:
                task = self.search_entity(
                    name=entity.get('name', ''),
                    address=entity.get('address', ''),
                    city=entity.get('city', ''),
                    state=entity.get('state', ''),
                    zip_code=entity.get('zip', ''),
                    country=entity.get('country', '')
                )
                search_tasks.append(task)
            
            # Execute all searches concurrently
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Batch search failed for entity {i}: {str(result)}")
                    processed_results.append({
                        'error': str(result),
                        'entity_index': i,
                        'entities': []
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"Error in batch OFAC search: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client session"""
        await self.http_client.aclose()


# Singleton instance
ofac_client = OfacClient()