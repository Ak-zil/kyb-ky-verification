import asyncio
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

import httpx
from app.utils.s3_storage import s3_storage



from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("persona")


class PersonaClient:
    """
    Client for Persona KYC/KYB API
    
    This implementation integrates with Persona's actual API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Persona client"""
        self.api_key = api_key or settings.PERSONA_API_KEY
        self.base_url = "https://api.withpersona.com/api/v1"
        self.logger = logger
        self.http_client = httpx.AsyncClient()

    async def get_inquiry(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Get inquiry details from Persona
        
        Args:
            inquiry_id: Persona inquiry ID
            
        Returns:
            Dict containing inquiry details
        """
        try:
            url = f"{self.base_url}/inquiries/{inquiry_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
            
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error getting Persona inquiry: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting Persona inquiry: {str(e)}")
            raise
    
    async def extract_business_info(self, inquiry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract business information from a Persona inquiry response
        
        Args:
            inquiry_data: The full Persona inquiry response
            
        Returns:
            Dict containing extracted business information
        """
        try:
            data = inquiry_data.get('data', {})
            attributes = data.get('attributes', {})
            fields = attributes.get('fields', {})
            
            # Extract business details
            business_info = {
                'business_name': fields.get('business-name', {}).get('value'),
                'business_tax_id': fields.get('business-tax-identification-number', {}).get('value'),
                'business_website': fields.get('business-website', {}).get('value'),
                'business_phone': fields.get('business-phone-number', {}).get('value'),
                'business_formation_date': fields.get('business-formation-date', {}).get('value'),
                'business_description': fields.get('business-description', {}).get('value'),
                'entity_type': fields.get('entity-type', {}).get('value'),
                'business_industry': fields.get('business-industry', {}).get('value'),
                'business_subindustry': fields.get(f"business-subindustry-{fields.get('business-industry', {}).get('value')}", {}).get('value'),
                'registration_number': fields.get('business-registration-number', {}).get('value'),
                
                # Business address
                'address': {
                    'street_1': fields.get('business-physical-address-street-1', {}).get('value'),
                    'street_2': fields.get('business-physical-address-street-2', {}).get('value'),
                    'city': fields.get('business-physical-address-city', {}).get('value'),
                    'state': fields.get('business-physical-address-subdivision', {}).get('value'),
                    'postal_code': fields.get('business-physical-address-postal-code', {}).get('value'),
                    'country_code': fields.get('business-physical-address-country-code', {}).get('value'),
                }
            }
            
            # Extract control person and UBO details
            control_person = {
                'name_first': fields.get('control-person-name-first', {}).get('value'),
                'name_last': fields.get('control-person-name-last', {}).get('value'),
                'email': fields.get('control-person-email-address', {}).get('value'),
                'job_title': fields.get('control-person-job-title', {}).get('value'),
                'is_also_owner': fields.get('control-person-is-also-owner', {}).get('value'),
                'percentage_ownership': fields.get('control-person-percentage-ownership', {}).get('value'),
                'country_code': fields.get('control-person-id-country-code', {}).get('value'),
            }
            
            # Extract UBOs (Ultimate Beneficial Owners)
            ubos = []
            for i in range(1, 5):  # Assuming there can be up to 4 UBOs
                ubo_name_first = fields.get(f'ubo-{i}-name-first', {}).get('value')
                
                if ubo_name_first:  # Only add if there's at least a first name
                    ubo = {
                        'name_first': ubo_name_first,
                        'name_last': fields.get(f'ubo-{i}-name-last', {}).get('value'),
                        'email': fields.get(f'ubo-{i}-email-address', {}).get('value'),
                        'job_title': fields.get(f'ubo-{i}-job-title', {}).get('value'),
                        'percentage_ownership': fields.get(f'ubo-{i}-percentage-ownership', {}).get('value'),
                        'association': fields.get(f'ubo-{i}-association', {}).get('value'),
                        'country_code': fields.get(f'ubo-{i}-id-country-code', {}).get('value'),
                    }
                    ubos.append(ubo)
            
            # Extract verification status
            verifications = []
            included = inquiry_data.get('included', [])
            for item in included:
                if item.get('type', '').startswith('verification/'):
                    verification = {
                        'type': item.get('type'),
                        'id': item.get('id'),
                        'status': item.get('attributes', {}).get('status')
                    }
                    verifications.append(verification)
            
            # Extract reports
            reports = []
            for item in included:
                if item.get('type', '').startswith('report/'):
                    report = {
                        'type': item.get('type'),
                        'id': item.get('id'),
                        'status': item.get('attributes', {}).get('status'),
                        'has_match': item.get('attributes', {}).get('has-match')
                    }
                    reports.append(report)
            
            # Get watchlist report details if available
            watchlist_details = {}
            for item in included:
                if item.get('type') == 'report/watchlist':
                    watchlist_details = {
                        'has_match': item.get('attributes', {}).get('has-match', False),
                        'matched_lists': item.get('attributes', {}).get('matched-lists', [])
                    }
            
            # Get business classification details if available
            classification_details = {}
            for item in included:
                if item.get('type') == 'report/business-classification':
                    if item.get('attributes', {}).get('result'):
                        result = item.get('attributes', {}).get('result', {})
                        classification_details = {
                            'naics_codes': [code.get('code') for code in result.get('naics-information', [])],
                            'mcc_codes': [code.get('code') for code in result.get('mcc-information', [])],
                            'keywords': result.get('keywords', []),
                            'is_high_risk': result.get('is-high-risk', False)
                        }
            
            # Compile the full result
            result = {
                'inquiry_id': data.get('id'),
                'status': attributes.get('status'),
                'created_at': attributes.get('created-at'),
                'completed_at': attributes.get('completed-at'),
                'business_info': business_info,
                'control_person': control_person,
                'beneficial_owners': ubos,
                'verifications': verifications,
                'reports': reports,
                'watchlist_details': watchlist_details,
                'classification_details': classification_details
            }
            
            return result
        except Exception as e:
            self.logger.error(f"Error extracting business info: {str(e)}")
            raise
    
    async def get_business_details(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Get combined business details from a Persona inquiry
        
        Args:
            inquiry_id: Persona inquiry ID
            
        Returns:
            Dict containing structured business information
        """
        try:
            # Get the full inquiry data
            inquiry_data = await self.get_inquiry(inquiry_id)
            
            # Extract the business info
            business_details = await self.extract_business_info(inquiry_data)
            
            return business_details
        except Exception as e:
            self.logger.error(f"Error getting business details: {str(e)}")
            raise

    async def create_inquiry(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new inquiry in Persona
        
        Args:
            attributes: Dictionary with inquiry attributes
            
        Returns:
            Dict containing the created inquiry details
        """
        try:
            url = f"{self.base_url}/inquiries"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "data": {
                    "type": "inquiry",
                    "attributes": attributes
                }
            }
            
            response = await self.http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error creating Persona inquiry: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating Persona inquiry: {str(e)}")
            raise

    async def update_inquiry(self, inquiry_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing inquiry in Persona
        
        Args:
            inquiry_id: Persona inquiry ID
            attributes: Dictionary with inquiry attributes to update
            
        Returns:
            Dict containing the updated inquiry details
        """
        try:
            url = f"{self.base_url}/inquiries/{inquiry_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "data": {
                    "type": "inquiry",
                    "attributes": attributes
                }
            }
            
            response = await self.http_client.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error updating Persona inquiry: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating Persona inquiry: {str(e)}")
            raise

    async def list_inquiries(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        List inquiries from Persona with optional filtering
        
        Args:
            params: Optional query parameters for filtering
            
        Returns:
            Dict containing list of inquiries
        """
        try:
            url = f"{self.base_url}/inquiries"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error listing Persona inquiries: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing Persona inquiries: {str(e)}")
            raise

    async def get_verification(self, verification_id: str) -> Dict[str, Any]:
        """
        Get verification details from Persona
        
        Args:
            verification_id: Persona verification ID
            
        Returns:
            Dict containing verification details
        """
        try:
            url = f"{self.base_url}/verifications/{verification_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.http_client.get(url, headers=headers)
            response.raise_for_status()
            
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error getting Persona verification: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting Persona verification: {str(e)}")
            raise


    async def get_and_store_documents(self, inquiry_id: str) -> Dict[str, Any]:
        """
        Get document files from a Persona inquiry and store them in S3
        
        Args:
            inquiry_id: Persona inquiry ID
            
        Returns:
            Dict containing document information with S3 URLs
        """
        try:
            # Get the full inquiry data
            inquiry_data = await self.get_inquiry(inquiry_id)
            
            

            # Extract documents from the 'included' section
            included = inquiry_data.get('included', [])

            
            documents = []
            
            for item in included:
                if 'document' in item.get('type'):
                    doc_id = item.get('id')
                    attributes = item.get('attributes', {})
                    
                    # Initialize document info
                    document = {
                        'id': doc_id,
                        'name': attributes.get('kind', 'Unknown Document'),
                        'status': attributes.get('status'),
                        'created_at': attributes.get('created-at'),
                    }
                    

                    

                    # Extract file info - files array has priority, then files-normalized
                    file_info = None
                    if 'files' in attributes and attributes['files']:
                        file_info = attributes['files'][0]  # Use the first file in the array
                    elif 'files-normalized' in attributes and attributes['files-normalized']:
                        file_info = attributes['files-normalized'][0]  # Use the first normalized file
                    
                    if file_info:
                        document['filename'] = file_info.get('filename')
                        document['file_url'] = file_info.get('url')
                        document['byte_size'] = file_info.get('byte-size')
                    
                    # Add document checks if they exist
                    if 'checks' in attributes:
                        document['checks'] = attributes.get('checks', [])
                    
                    # If there's a file URL, download and store the file
                    if document.get('file_url'):
                        try:
                            # Download file from Persona
                            response = await self.http_client.get(document['file_url'])
                            response.raise_for_status()
                            file_content = response.content
                            
                            # Determine content type
                            content_type = response.headers.get('Content-Type', 'application/octet-stream')
                            
                            # Generate filename
                            file_name = document.get('filename') or f"{doc_id}_{document['name']}"
                            
                            # Store in S3
                            s3_result = await s3_storage.upload_document(
                                file_content=file_content,
                                file_name=file_name,
                                content_type=content_type,
                                metadata={
                                    'document_id': doc_id,
                                    'inquiry_id': inquiry_id
                                }
                            )
                            
                            # Add S3 info to document
                            document['s3_url'] = s3_result['s3_url']
                            document['s3_key'] = s3_result['key']
                            
                        except Exception as e:
                            self.logger.error(f"Error downloading and storing document: {str(e)}")
                            document['error'] = str(e)
                    
                    documents.append(document)
            
            return {
                'inquiry_id': inquiry_id,
                'documents': documents
            }
        
        except Exception as e:
            self.logger.error(f"Error getting and storing documents: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client session"""
        await self.http_client.aclose()



persona_client = PersonaClient()