from datetime import datetime
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("sift")


class SiftClient:
    """
    Client for Sift Science fraud detection API
    
    This is a mock implementation for demonstration purposes.
    In a real application, this would integrate with Sift's API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Sift client"""
        self.api_key = api_key or settings.SIFT_API_KEY
        self.base_url = "https://api.sift.com/v205"
        self.logger = logger

    async def get_user_score(self, user_id: str) -> Dict[str, Any]:
        """
        Get user risk score from Sift
        
        Args:
            user_id: User ID
            
        Returns:
            Dict containing user risk score and details
        """
        try:
            # This is a mock response
            # In a real implementation, this would call Sift's API
            return {
                "status": 0,
                "error_message": "OK",
                "score": 65,
                "scores": {
                    "payment_abuse": 42,
                    "promotion_abuse": 30,
                    "account_abuse": 22,
                    "content_abuse": 15
                },
                "workflow_statuses": [],
                "latest_decisions": {},
                "user": {
                    "id": f"user_{user_id}",
                    "network": {
                        "risk_score": 45,
                        "associated_users": [
                            {
                                "id": f"user_associated_{user_id}",
                                "association_type": "ip_address",
                                "association_strength": "medium"
                            }
                        ]
                    },
                    "activities": [
                        {
                            "type": "login",
                            "time": int(datetime.utcnow().timestamp()),
                            "ip": "192.168.1.1",
                            "status": "success"
                        },
                        {
                            "type": "transaction",
                            "time": int(datetime.utcnow().timestamp()),
                            "amount": 150,
                            "currency": "USD",
                            "status": "success"
                        }
                    ]
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting Sift user score: {str(e)}")
            raise

    async def get_open_corporates_data(
        self, 
        business_name: str, 
        country: str
    ) -> Dict[str, Any]:
        """
        Get business data from Open Corporates
        
        Args:
            business_name: Business name
            country: Country code
            
        Returns:
            Dict containing business data
        """
        try:
            # This is a mock response
            # In a real implementation, this would call Open Corporates API
            return {
                "business_name": business_name,
                "business_type": "technology",
                "industry": "software",
                "registration_number": f"REG{business_name.replace(' ', '')}",
                "country": country,
                "status": "active",
                "incorporation_date": "2020-01-15",
                "last_filing_date": "2023-05-20"
            }
        except Exception as e:
            self.logger.error(f"Error getting Open Corporates data: {str(e)}")
            raise


# Create singleton instance
sift_client = SiftClient()