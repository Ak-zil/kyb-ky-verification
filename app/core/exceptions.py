from fastapi import HTTPException, status


class VerificationError(Exception):
    """Base exception for verification errors"""
    pass


class AgentExecutionError(VerificationError):
    """Exception for errors during agent execution"""
    pass


class AuthenticationError(HTTPException):
    """Exception for authentication errors"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class APIKeyError(HTTPException):
    """Exception for API key errors"""
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class PermissionDeniedError(HTTPException):
    """Exception for permission denied errors"""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundError(HTTPException):
    """Exception for not found errors"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class DataValidationError(HTTPException):
    """Exception for data validation errors"""
    def __init__(self, detail: str = "Invalid data"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )