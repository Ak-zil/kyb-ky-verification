import json
from datetime import date, datetime
from typing import Any


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles date and datetime objects.
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert date and datetime objects to ISO format strings.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def serialize_json(obj: Any) -> str:
    """
    Serialize an object to JSON, handling dates and datetimes.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON string
    """
    return json.dumps(obj, cls=CustomJSONEncoder)


def convert_dates_to_strings(obj: Any) -> Any:
    """
    Recursively convert date and datetime objects to strings in a nested structure.
    
    Args:
        obj: Object to convert
        
    Returns:
        Object with dates converted to strings
    """
    if isinstance(obj, dict):
        return {k: convert_dates_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates_to_strings(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    return obj