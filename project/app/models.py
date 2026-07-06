"""
Pydantic models for the Prescription Authenticator AI system
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    """User roles in the system"""

    CLINICIAN = "clinician"
    PHARMACIST = "pharmacist"
    ADMIN = "admin"


class User(BaseModel):
    """User model for authentication"""

    username: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool = True
    created_at: Optional[datetime] = None


class Token(BaseModel):
    """JWT token response model"""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data"""

    username: Optional[str] = None


class PatientInfo(BaseModel):
    """Patient information for prescription analysis"""

    age: int = Field(..., ge=0, le=150, description="Patient age in years")
    weight_kg: float = Field(
        ..., ge=0.5, le=500, description="Patient weight in kilograms"
    )
    allergies: List[str] = Field(default=[], description="List of known allergies")
    medical_conditions: List[str] = Field(
        default=[], description="List of medical conditions"
    )

    @validator("allergies", "medical_conditions")
    def clean_lists(cls, v):
        """Clean and normalize list items"""
        if v is None:
            return []
        return [item.strip().lower() for item in v if item.strip()]


class ExtractedMedication(BaseModel):
    """Medication extracted from prescription text"""

    drug_name: str = Field(..., description="Name of the medication")
    strength: Optional[str] = Field(
        None, description="Medication strength (e.g., '100mg')"
    )
    frequency: Optional[str] = Field(
        None, description="Dosing frequency (e.g., 'BID', 'TID')"
    )
    duration: Optional[str] = Field(
        None, description="Treatment duration (e.g., '7 days')"
    )
    route: Optional[str] = Field(
        None, description="Route of administration (e.g., 'oral')"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Extraction confidence score"
    )

    @validator("drug_name")
    def clean_drug_name(cls, v):
        """Clean and normalize drug name"""
        return v.strip().title()


class RxNormMapping(BaseModel):
    """RxNorm database mapping for medications"""

    rxcui: str = Field(..., description="RxNorm Concept Unique Identifier")
    name: str = Field(..., description="Standardized drug name")
    synonym: Optional[str] = Field(None, description="Alternative name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence")


class SafetyAlert(BaseModel):
    """Safety alert for medication dosing"""

    severity: str = Field(
        ..., description="Alert severity: low, medium, high, critical"
    )
    message: str = Field(..., description="Alert message")
    recommendation: str = Field(..., description="Recommended action")
    reference: Optional[str] = Field(None, description="Reference or guideline source")

    @validator("severity")
    def validate_severity(cls, v):
        """Validate severity levels"""
        allowed = ["low", "medium", "high", "critical"]
        if v.lower() not in allowed:
            raise ValueError(f"Severity must be one of: {allowed}")
        return v.lower()


class DrugInteraction(BaseModel):
    """Drug-drug interaction information"""

    drug1: str = Field(..., description="First medication")
    drug2: str = Field(..., description="Second medication")
    severity: str = Field(..., description="Interaction severity")
    description: str = Field(..., description="Interaction description")
    recommendation: str = Field(..., description="Clinical recommendation")
    source: Optional[str] = Field(None, description="Information source")


class AlternativeMedication(BaseModel):
    """Alternative medication suggestion"""

    drug_name: str = Field(..., description="Alternative medication name")
    reason: str = Field(..., description="Reason for suggesting this alternative")
    strength: Optional[str] = Field(None, description="Suggested strength")
    route: Optional[str] = Field(None, description="Route of administration")
    notes: Optional[str] = Field(None, description="Additional notes")


class PrescriptionAnalysisRequest(BaseModel):
    """Request model for prescription analysis"""

    text: str = Field(..., min_length=1, description="Prescription text to analyze")
    patient: PatientInfo = Field(..., description="Patient information")
    include_alternatives: bool = Field(
        True, description="Include alternative medication suggestions"
    )

    @validator("text")
    def clean_text(cls, v):
        """Clean prescription text"""
        return v.strip()


class PrescriptionAnalysisResponse(BaseModel):
    """Response model for prescription analysis"""

    extracted_medications: List[ExtractedMedication] = Field(
        ..., description="Extracted medications"
    )
    rxnorm_mappings: List[RxNormMapping] = Field(
        default=[], description="RxNorm mappings"
    )
    safety_alerts: List[SafetyAlert] = Field(default=[], description="Safety alerts")
    drug_interactions: List[DrugInteraction] = Field(
        default=[], description="Drug interactions"
    )
    suggested_alternatives: List[AlternativeMedication] = Field(
        default=[], description="Alternative medications"
    )
    analysis_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall analysis confidence"
    )
    processing_time_ms: Optional[float] = Field(
        None, description="Processing time in milliseconds"
    )


class RxNormLookupResponse(BaseModel):
    """Response model for RxNorm drug lookup"""

    query: str = Field(..., description="Original search query")
    candidates: List[RxNormMapping] = Field(..., description="Found candidates")
    total_results: int = Field(..., description="Total number of results")


class RxCuiLookupResponse(BaseModel):
    """Response model for RxCUI lookup by drug name"""

    query: str = Field(..., description="Drug name queried")
    rxcuis: List[str] = Field(default_factory=list, description="List of RxCUI identifiers")


class DrugInteractionsRequest(BaseModel):
    """Request model for checking drug interactions given RxCUIs"""

    rxcuis: List[str] = Field(..., description="List of RxCUI identifiers")


class DrugInteractionsResponse(BaseModel):
    """Response model for drug interactions lookup"""

    interactions: List[DrugInteraction] = Field(default_factory=list, description="Found interactions")
    total_results: int = Field(..., description="Total number of interactions found")


class HealthCheckResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Response timestamp")
    services: Optional[Dict[str, str]] = Field(
        None, description="Service status details"
    )


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: str = Field(..., description="Error timestamp")


class OCRRequest(BaseModel):
    """Request model for OCR text extraction"""

    image_data: str = Field(..., description="Base64 encoded image data")
    image_format: str = Field(..., description="Image format (png, jpg, etc.)")

    @validator("image_format")
    def validate_format(cls, v):
        """Validate image format"""
        allowed = ["png", "jpg", "jpeg", "tiff", "bmp"]
        if v.lower() not in allowed:
            raise ValueError(f"Image format must be one of: {allowed}")
        return v.lower()


class OCRResponse(BaseModel):
    """Response model for OCR text extraction"""

    extracted_text: str = Field(..., description="Extracted text from image")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score")
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
