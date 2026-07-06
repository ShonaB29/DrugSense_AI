#!/usr/bin/env python3
"""
Minimal backend for testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="Prescription Authenticator AI", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PatientInfo(BaseModel):
    age: int
    weight_kg: float
    allergies: List[str] = []

class ExtractedMedication(BaseModel):
    drug_name: str
    strength: str = None
    frequency: str = None
    duration: str = None
    confidence: float = 0.8

class AnalysisRequest(BaseModel):
    text: str
    patient: PatientInfo

class AnalysisResponse(BaseModel):
    extracted_medications: List[ExtractedMedication]
    rxnorm_mappings: List[dict] = []
    safety_alerts: List[dict] = []
    drug_interactions: List[dict] = []
    suggested_alternatives: List[dict] = []
    analysis_confidence: float = 0.8

@app.get("/")
def root():
    return {"status": "healthy", "message": "Prescription Authenticator AI"}

@app.get("/health")
def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/token")
def login():
    return {"access_token": "demo-token", "token_type": "bearer"}

@app.post("/api/v1/analyze")
def analyze_prescription(request: AnalysisRequest):
    # Simple regex extraction
    import re
    text = request.text.lower()
    
    medications = []
    
    # Look for common patterns
    patterns = [
        r'(aspirin|ibuprofen|acetaminophen|amoxicillin)\s+(\d+\s*mg)\s+(od|bd|tds)\s*(?:for\s+)?(\d+\s*days?)?',
        r'(aspirin|ibuprofen|acetaminophen|amoxicillin)\s+(\d+\s*mg)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            groups = match.groups()
            med = ExtractedMedication(
                drug_name=groups[0].title(),
                strength=groups[1] if len(groups) > 1 else None,
                frequency=groups[2].upper() if len(groups) > 2 else None,
                duration=groups[3] if len(groups) > 3 else None,
                confidence=0.9
            )
            medications.append(med)
    
    # If no patterns found, try simple drug names
    if not medications:
        drugs = ['aspirin', 'ibuprofen', 'acetaminophen', 'amoxicillin']
        for drug in drugs:
            if drug in text:
                medications.append(ExtractedMedication(
                    drug_name=drug.title(),
                    confidence=0.7
                ))
    
    # Add some demo safety alerts
    alerts = []
    if request.patient.age > 65:
        alerts.append({
            "severity": "medium",
            "message": "Consider dose adjustment for elderly patient",
            "recommendation": "Monitor for side effects"
        })
    
    return AnalysisResponse(
        extracted_medications=medications,
        safety_alerts=alerts,
        analysis_confidence=0.8 if medications else 0.3
    )

@app.get("/api/v1/rxnorm/lookup")
def rxnorm_lookup(q: str):
    # Demo data
    candidates = [
        {"rxcui": "1191", "name": "Aspirin", "confidence": 0.95},
        {"rxcui": "5640", "name": "Ibuprofen", "confidence": 0.90},
    ]
    
    return {"query": q, "candidates": candidates}

if __name__ == "__main__":
    print("🚀 Starting Minimal Backend...")
    print("📊 API: http://localhost:8000")
    print("📋 Docs: http://localhost:8000/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
