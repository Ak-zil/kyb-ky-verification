from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, 
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.session import Base


class Verification(Base):
    """
    Verification model for storing verification records
    """
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String, unique=True, index=True, nullable=False)
    business_id = Column(String, index=True, nullable=True)
    user_id = Column(String, index=True, nullable=True)
    status = Column(String, nullable=False, default="pending")
    result = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    verification_data = relationship("VerificationData", back_populates="verification", uselist=False)
    verification_results = relationship("VerificationResult", back_populates="verification")
    ubo_verifications = relationship("UboVerification", back_populates="verification")


class VerificationData(Base):
    """
    Storage for verification data
    """
    __tablename__ = "verification_data"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String, ForeignKey("verifications.verification_id"), nullable=False)
    data_type = Column(String, nullable=False)  # e.g., "user_data", "business_data"
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    verification = relationship("Verification", back_populates="verification_data")


class VerificationResult(Base):
    """
    Verification result model for storing agent check results
    """
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String, ForeignKey("verifications.verification_id"), nullable=False)
    agent_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    checks = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    verification = relationship("Verification", back_populates="verification_results")


class UboVerification(Base):
    """
    Model for linking business verification to UBO verifications
    """
    __tablename__ = "ubo_verifications"

    id = Column(Integer, primary_key=True, index=True)
    verification_id = Column(String, ForeignKey("verifications.verification_id"), nullable=False)
    ubo_user_id = Column(String, nullable=False)
    ubo_verification_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    verification = relationship("Verification", back_populates="ubo_verifications")