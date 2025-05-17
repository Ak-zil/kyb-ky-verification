from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field


# Verification Request Schemas
class KycVerificationRequest(BaseModel):
    user_id: str
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BusinessVerificationRequest(BaseModel):
    business_id: str
    additional_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Verification Response Schemas
class VerificationResponse(BaseModel):
    verification_id: str
    status: str


class VerificationStatusResponse(BaseModel):
    verification_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class VerificationCheck(BaseModel):
    agent_type: str
    check_name: str
    status: str
    details: Optional[str] = None


class UboVerificationReport(BaseModel):
    user_id: str
    verification_id: str
    status: str
    result: Optional[str] = None
    reason: Optional[str] = None


class VerificationResults(BaseModel):
    overall_status: Optional[str] = None
    verification_checks: List[VerificationCheck]
    summary: Optional[str] = None
    ubo_reports: Optional[List[UboVerificationReport]] = None


class VerificationReportResponse(BaseModel):
    verification_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    results: VerificationResults


# Agent Result Schema
class AgentResult(BaseModel):
    agent_type: str
    status: str
    details: str
    checks: Optional[List[Dict[str, Any]]] = None
    data: Optional[Dict[str, Any]] = None
    verification_result: Optional[str] = None
    reasoning: Optional[str] = None