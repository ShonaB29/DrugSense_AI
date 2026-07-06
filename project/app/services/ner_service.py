"""
Medical Named Entity Recognition (NER) service using Hugging Face transformers
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch
from functools import lru_cache

from app.core.config import get_settings
from app.models import ExtractedMedication

logger = logging.getLogger(__name__)


class MedicalNERService:
    """Medical NER service for extracting medications from prescription text"""

    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.tokenizer = None
        self.ner_pipeline = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the Hugging Face NER model"""
        try:
            logger.info(f"Loading medical NER model: {self.settings.hf_model_name}")

            # Use CPU for compatibility
            device = 0 if torch.cuda.is_available() else -1

            # Initialize the NER pipeline with correct parameters
            self.ner_pipeline = pipeline(
                "ner",
                model=self.settings.hf_model_name,
                tokenizer=self.settings.hf_model_name,
                aggregation_strategy="simple",
                device=device,
            )

            logger.info("Medical NER model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load NER model: {e}")
            logger.info("Falling back to regex-based extraction")
            self.ner_pipeline = None

    def extract_medications(self, text: str) -> List[ExtractedMedication]:
        """Extract medications from prescription text"""
        try:
            # Clean and preprocess text
            cleaned_text = self._preprocess_text(text)

            # Try Hugging Face model first
            if self.ner_pipeline:
                medications = self._extract_with_hf_model(cleaned_text)
                if medications:
                    return medications

            # Fallback to regex-based extraction
            logger.info("Using regex-based medication extraction")
            return self._extract_with_regex(cleaned_text)

        except Exception as e:
            logger.error(f"Error extracting medications: {e}")
            return []

    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess prescription text"""
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text.strip())

        # Normalize common abbreviations
        abbreviations = {
            "od": "once daily",
            "bd": "twice daily",
            "bid": "twice daily",
            "tid": "three times daily",
            "qid": "four times daily",
            "qds": "four times daily",
            "prn": "as needed",
            "po": "by mouth",
            "iv": "intravenous",
            "im": "intramuscular",
            "sc": "subcutaneous",
        }

        for abbrev, full in abbreviations.items():
            text = re.sub(rf"\b{abbrev}\b", full, text, flags=re.IGNORECASE)

        return text

    def _extract_with_hf_model(self, text: str) -> List[ExtractedMedication]:
        """Extract medications using Hugging Face NER model"""
        try:
            # Get NER predictions
            entities = self.ner_pipeline(text)

            medications = []
            current_medication = {}

            for entity in entities:
                label = entity["entity_group"].upper()
                word = entity["word"]
                confidence = entity["score"]

                # Map entity labels to our medication fields
                if label in ["DRUG", "MEDICATION", "CHEMICAL"]:
                    if current_medication:
                        medications.append(self._create_medication(current_medication))
                    current_medication = {"drug_name": word, "confidence": confidence}
                elif label in ["DOSAGE", "STRENGTH"] and current_medication:
                    current_medication["strength"] = word
                elif label in ["FREQUENCY"] and current_medication:
                    current_medication["frequency"] = word
                elif label in ["DURATION"] and current_medication:
                    current_medication["duration"] = word

            # Add the last medication
            if current_medication:
                medications.append(self._create_medication(current_medication))

            return medications

        except Exception as e:
            logger.error(f"Error in HF model extraction: {e}")
            return []

    def _extract_with_regex(self, text: str) -> List[ExtractedMedication]:
        """Extract medications using regex patterns"""
        medications = []
        
        try:
            # Enhanced regex patterns for medication extraction
            patterns = [
                # Pattern 1: Drug Name + Strength + Frequency + Duration
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?))\s+(?:(\w+)\s+)?(?:for\s+)?(\d+\s*(?:days?|weeks?|months?|hours?))',
                
                # Pattern 2: Drug Name + Strength + Frequency
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?))\s+(\w+)',
                
                # Pattern 3: Drug Name + Strength
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?))',
                
                # Pattern 4: Drug Name + Frequency + Duration
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\w+)\s+(?:for\s+)?(\d+\s*(?:days?|weeks?|months?|hours?))',
                
                # Pattern 5: Drug Name + Frequency
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\w+)',
                
                # Pattern 6: Just Drug Name (fallback)
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
            ]
            
            # Common medication names to look for
            common_meds = [
                'aspirin', 'ibuprofen', 'acetaminophen', 'paracetamol', 'amoxicillin',
                'penicillin', 'warfarin', 'insulin', 'metformin', 'lisinopril',
                'atorvastatin', 'omeprazole', 'pantoprazole', 'metoprolol',
                'amlodipine', 'hydrochlorothiazide', 'furosemide', 'spironolactone',
                'digoxin', 'phenytoin', 'carbamazepine', 'valproate', 'lithium',
                'morphine', 'codeine', 'tramadol', 'oxycodone', 'hydrocodone',
                'diazepam', 'alprazolam', 'lorazepam', 'clonazepam', 'zolpidem',
                'sertraline', 'fluoxetine', 'escitalopram', 'venlafaxine', 'bupropion',
                'quetiapine', 'risperidone', 'olanzapine', 'aripiprazole'
            ]
            
            # Frequency abbreviations
            frequency_map = {
                'od': 'once daily',
                'bd': 'twice daily', 
                'bid': 'twice daily',
                'tid': 'three times daily',
                'qid': 'four times daily',
                'qds': 'four times daily',
                'prn': 'as needed',
                'daily': 'once daily',
                'twice': 'twice daily',
                'thrice': 'three times daily'
            }
            
            # Route abbreviations
            route_map = {
                'po': 'oral',
                'iv': 'intravenous',
                'im': 'intramuscular',
                'sc': 'subcutaneous',
                'top': 'topical',
                'inh': 'inhalation'
            }
            
            # Try pattern matching first
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 1 and groups[0]:
                        drug_name = groups[0].strip()
                        
                        # Skip if it's not a medication
                        if not self._is_medication(drug_name, common_meds):
                            continue
                        
                        # Extract components
                        strength = groups[1] if len(groups) > 1 and groups[1] else None
                        frequency = groups[2] if len(groups) > 2 and groups[2] else None
                        duration = groups[3] if len(groups) > 3 and groups[3] else None
                        
                        # Normalize frequency and route
                        if frequency:
                            frequency = frequency_map.get(frequency.lower(), frequency)
                        
                        # Determine route (default to oral)
                        route = 'oral'
                        if strength and any(route_abbr in text.lower() for route_abbr in route_map):
                            for route_abbr, route_name in route_map.items():
                                if route_abbr in text.lower():
                                    route = route_name
                                    break
                        
                        # Calculate confidence based on extracted information
                        confidence = 0.6  # Base confidence for regex
                        if strength:
                            confidence += 0.2
                        if frequency:
                            confidence += 0.1
                        if duration:
                            confidence += 0.1
                        
                        medication = ExtractedMedication(
                            drug_name=drug_name,
                            strength=strength,
                            frequency=frequency,
                            duration=duration,
                            route=route,
                            confidence=min(confidence, 0.95)  # Cap at 0.95
                        )
                        
                        # Avoid duplicates
                        if not any(med.drug_name.lower() == drug_name.lower() for med in medications):
                            medications.append(medication)
            
            # If no medications found with patterns, try direct lookup
            if not medications:
                for med_name in common_meds:
                    if med_name in text.lower():
                        medication = ExtractedMedication(
                            drug_name=med_name.title(),
                            strength=None,
                            frequency=None,
                            duration=None,
                            route='oral',
                            confidence=0.5
                        )
                        medications.append(medication)
            
            logger.info(f"Regex extraction found {len(medications)} medications")
            return medications
            
        except Exception as e:
            logger.error(f"Error in regex extraction: {e}")
            return []
    
    def _is_medication(self, text: str, common_meds: List[str]) -> bool:
        """Check if extracted text is likely a medication"""
        text_lower = text.lower()
        
        # Check against common medication names
        if any(med in text_lower for med in common_meds):
            return True
        
        # Check for common medication suffixes
        med_suffixes = ['ine', 'ol', 'ide', 'ate', 'am', 'il', 'in', 'an']
        if any(text_lower.endswith(suffix) for suffix in med_suffixes):
            return True
        
        # Check for common medication prefixes
        med_prefixes = ['met', 'lis', 'ome', 'panto', 'hydro', 'spiro']
        if any(text_lower.startswith(prefix) for prefix in med_prefixes):
            return True
        
        # Skip common non-medication words
        non_med_words = ['tablet', 'capsule', 'injection', 'cream', 'ointment', 'dose', 'take']
        if any(word in text_lower for word in non_med_words):
            return False
        
        return True

    def _create_medication(self, data: Dict[str, Any]) -> ExtractedMedication:
        """Create ExtractedMedication object from extracted data"""
        return ExtractedMedication(
            drug_name=data.get("drug_name", ""),
            strength=data.get("strength"),
            frequency=data.get("frequency"),
            duration=data.get("duration"),
            route=data.get("route", "oral"),  # Default to oral
            confidence=min(data.get("confidence", 0.7), 1.0),
        )

    @lru_cache(maxsize=100)
    def _normalize_drug_name(self, drug_name: str) -> str:
        """Normalize drug name for better matching"""
        # Remove common suffixes
        suffixes = ["tablet", "capsule", "syrup", "injection", "cream", "ointment"]
        normalized = drug_name.lower().strip()

        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        return normalized.title()

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "model_name": self.settings.hf_model_name,
            "model_loaded": self.ner_pipeline is not None,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "cache_dir": self.settings.hf_cache_dir,
        }


# Global service instance
_ner_service: Optional[MedicalNERService] = None


def get_ner_service() -> MedicalNERService:
    """Get NER service instance (singleton pattern)"""
    global _ner_service
    if _ner_service is None:
        _ner_service = MedicalNERService()
    return _ner_service


def reload_ner_service() -> MedicalNERService:
    """Reload NER service (useful for testing)"""
    global _ner_service
    _ner_service = MedicalNERService()
    return _ner_service
