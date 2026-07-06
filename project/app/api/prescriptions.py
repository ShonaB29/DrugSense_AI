from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
import logging
from app.models import (
    PrescriptionAnalysisRequest, 
    PrescriptionAnalysisResponse,
    RxNormLookupResponse,
    RxCuiLookupResponse,
    DrugInteractionsRequest,
    DrugInteractionsResponse,
    User,
    ExtractedMedication,
    RxNormMapping,
    SafetyAlert,
    DrugInteraction,
    AlternativeMedication,
    OCRRequest,
    OCRResponse
)
from app.core.auth import get_current_active_user
from app.services.ner_service import get_ner_service, MedicalNERService
from app.services.rxnorm import get_rxnorm_service, RxNormService
from app.services.ocr_service import OCRService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["prescriptions"])

# Initialize OCR service
ocr_service = OCRService()


@router.post("/analyze", response_model=PrescriptionAnalysisResponse)
async def analyze_prescription(
    request: PrescriptionAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    ner_service: MedicalNERService = Depends(get_ner_service),
    rxnorm_service: RxNormService = Depends(get_rxnorm_service)
):
    """
    Analyze prescription text and extract medications with safety checks
    """
    try:
        logger.info(f"Analyzing prescription for user: {current_user.username}")
        
        # Step 1: Extract medications using NER
        extracted_medications = ner_service.extract_medications(request.text)
        
        if not extracted_medications:
            raise HTTPException(
                status_code=400, 
                detail="No medications found in the provided text"
            )
        
        # Step 2: Map medications to RxNorm
        rxnorm_mappings = []
        rxcuis = []
        
        for medication in extracted_medications:
            mappings = rxnorm_service.search_drug(medication.drug_name, max_results=3)
            rxnorm_mappings.extend(mappings)
            
            # Collect RxCUIs for interaction checking
            if mappings:
                rxcuis.append(mappings[0].rxcui)  # Use best match
        
        # Step 3: Check dosage safety
        safety_alerts = []
        for medication in extracted_medications:
            alerts = rxnorm_service.check_dosage_safety(
                medication, 
                request.patient.age, 
                request.patient.weight_kg
            )
            safety_alerts.extend(alerts)
        
        # Step 4: Check drug interactions
        drug_interactions = rxnorm_service.get_drug_interactions(rxcuis)
        
        # Step 5: Suggest alternatives
        suggested_alternatives = []
        for medication in extracted_medications:
            alternatives = rxnorm_service.suggest_alternatives(
                medication, 
                request.patient.allergies
            )
            suggested_alternatives.extend(alternatives)
        
        # Calculate overall analysis confidence
        if extracted_medications:
            analysis_confidence = sum(med.confidence for med in extracted_medications) / len(extracted_medications)
        else:
            analysis_confidence = 0.0
        
        response = PrescriptionAnalysisResponse(
            extracted_medications=extracted_medications,
            rxnorm_mappings=rxnorm_mappings,
            safety_alerts=safety_alerts,
            drug_interactions=drug_interactions,
            suggested_alternatives=suggested_alternatives,
            analysis_confidence=analysis_confidence
        )
        
        logger.info(f"Analysis completed successfully for {len(extracted_medications)} medications")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing prescription: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during prescription analysis"
        )


@router.get("/rxnorm/lookup", response_model=RxNormLookupResponse)
async def lookup_rxnorm(
    q: str = Query(..., description="Drug name to search"),
    max_results: int = Query(5, ge=1, le=10, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    rxnorm_service: RxNormService = Depends(get_rxnorm_service)
):
    """
    Look up drug in RxNorm database and return top candidates with synonyms
    """
    try:
        logger.info(f"RxNorm lookup for: {q}")
        
        if not q.strip():
            raise HTTPException(
                status_code=400,
                detail="Query parameter 'q' cannot be empty"
            )
        
        candidates = rxnorm_service.search_drug(q, max_results=max_results)
        
        response = RxNormLookupResponse(
            query=q,
            candidates=candidates,
            total_results=len(candidates)
        )
        
        logger.info(f"Found {len(candidates)} candidates for '{q}'")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in RxNorm lookup: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during RxNorm lookup"
        )


@router.get("/rxnorm/rxcui", response_model=RxCuiLookupResponse)
async def get_rxcui(
    q: str = Query(..., description="Drug name to resolve to RxCUI"),
    current_user: User = Depends(get_current_active_user),
    rxnorm_service: RxNormService = Depends(get_rxnorm_service)
):
    """
    Resolve a drug name to one or more RxCUI identifiers using RxNav.
    """
    try:
        if not q.strip():
            raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")

        rxcuis = rxnorm_service.get_rxcui(q)
        return RxCuiLookupResponse(query=q, rxcuis=rxcuis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving RxCUI for '{q}': {e}")
        raise HTTPException(status_code=500, detail="Internal server error during RxCUI lookup")


@router.post("/rxnorm/interactions", response_model=DrugInteractionsResponse)
async def interactions(
    request: DrugInteractionsRequest,
    current_user: User = Depends(get_current_active_user),
    rxnorm_service: RxNormService = Depends(get_rxnorm_service)
):
    """
    Get drug-drug interactions for a list of RxCUI identifiers.
    """
    try:
        if not request.rxcuis or len(request.rxcuis) < 2:
            return DrugInteractionsResponse(interactions=[], total_results=0)

        interactions = rxnorm_service.get_drug_interactions(request.rxcuis)
        return DrugInteractionsResponse(interactions=interactions, total_results=len(interactions))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in interactions lookup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during interactions lookup")


@router.post("/ocr", response_model=OCRResponse)
async def extract_text_from_image(
    request: OCRRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Extract text from prescription image using OCR
    """
    try:
        logger.info(f"OCR request from user: {current_user.username}")
        
        # Extract text from image
        extracted_text, confidence = ocr_service.extract_text_from_image(
            request.image_data, 
            request.image_format
        )
        
        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the image"
            )
        
        # Calculate processing time (simplified)
        processing_time_ms = 100.0  # Placeholder
        
        response = OCRResponse(
            extracted_text=extracted_text,
            confidence=confidence,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"OCR completed successfully with confidence: {confidence:.2f}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OCR processing: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during OCR processing"
        )
