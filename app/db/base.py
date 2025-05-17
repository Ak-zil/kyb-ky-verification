
# Import all the models here so that alembic can discover them
from app.db.session import Base
from app.models.user import User
from app.models.apikey import APIKey
from app.models.verification import Verification, VerificationData
from app.models.results import VerificationResult, UboVerification