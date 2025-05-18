import re
from typing import Any, Dict, List, Optional, Union

from pydantic import EmailStr, validator

from app.core.exceptions import DataValidationError
from app.utils.logging import get_logger

logger = get_logger("validation")


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Use pydantic's EmailStr validation
        EmailStr.validate(email)
        return True
    except Exception:
        return False


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Basic validation for E.164 format
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))


def validate_business_id(business_id: str) -> bool:
    """
    Validate business ID format
    
    Args:
        business_id: Business ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # This is a placeholder - implement appropriate validation
    if not business_id:
        return False
    return True


def validate_user_id(user_id: str) -> bool:
    """
    Validate user ID format
    
    Args:
        user_id: User ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # This is a placeholder - implement appropriate validation
    if not user_id:
        return False
    return True


def validate_verification_request(data: Dict[str, Any], request_type: str) -> None:
    """
    Validate verification request data
    
    Args:
        data: Request data
        request_type: Type of request (kyc or business)
        
    Raises:
        DataValidationError: If validation fails
    """
    try:
        if request_type == "kyc":
            user_id = data.get("user_id")
            if not user_id:
                raise DataValidationError("user_id is required")
            
            if not validate_user_id(user_id):
                raise DataValidationError("Invalid user_id format")
                
        elif request_type == "business":
            business_id = data.get("business_id")
            if not business_id:
                raise DataValidationError("business_id is required")
            
            if not validate_business_id(business_id):
                raise DataValidationError("Invalid business_id format")
        
        # Validate additional_data if present
        additional_data = data.get("additional_data", {})
        if not isinstance(additional_data, dict):
            raise DataValidationError("additional_data must be an object")
            
    except DataValidationError:
        raise
    except Exception as e:
        logger.error(f"Error validating verification request: {str(e)}")
        raise DataValidationError(f"Error validating request: {str(e)}")