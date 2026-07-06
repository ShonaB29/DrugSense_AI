import requests
import logging
from typing import List, Optional, Dict, Any
from app.core.config import get_settings
from app.models import RxNormMapping, ExtractedMedication, SafetyAlert, DrugInteraction, AlternativeMedication
import re

logger = logging.getLogger(__name__)


class RxNormService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.rxnorm_api_base_url
        
    def get_rxcui(self, drug_name: str) -> List[str]:
        """Get RxCUI for a drug name using the correct endpoint"""
        try:
            # Clean the drug name to remove special characters that might cause API issues
            cleaned_name = re.sub(r'[^\w\s-]', '', drug_name).strip()
            
            if not cleaned_name:
                logger.warning(f"Drug name '{drug_name}' cleaned to empty string")
                return []
            
            url = f"{self.base_url}/rxcui.json?name={cleaned_name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rxcuis = data.get("idGroup", {}).get("rxnormId", [])
            
            if not isinstance(rxcuis, list):
                rxcuis = [rxcuis] if rxcuis else []
            
            logger.info(f"Found {len(rxcuis)} RxCUIs for {cleaned_name}: {rxcuis}")
            return rxcuis
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.warning(f"Bad request for drug name '{drug_name}': {e}")
                # Try with cleaned name if different from original
                if drug_name != cleaned_name:
                    try:
                        url = f"{self.base_url}/rxcui.json?name={cleaned_name}"
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()
                        
                        data = response.json()
                        rxcuis = data.get("idGroup", {}).get("rxnormId", [])
                        
                        if not isinstance(rxcuis, list):
                            rxcuis = [rxcuis] if rxcuis else []
                        
                        logger.info(f"Found {len(rxcuis)} RxCUIs for cleaned name '{cleaned_name}': {rxcuis}")
                        return rxcuis
                    except:
                        pass
            else:
                logger.error(f"HTTP error getting RxCUI for {drug_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting RxCUI for {drug_name}: {e}")
            return []
    
    def search_drug(self, drug_name: str, max_results: int = 5) -> List[RxNormMapping]:
        """Search for drug in RxNorm database"""
        try:
            # Get RxCUIs first
            rxcuis = self.get_rxcui(drug_name)
            
            mappings = []
            for rxcui in rxcuis[:max_results]:
                # Get drug details
                drug_info = self._get_drug_info(rxcui)
                if drug_info:
                    mapping = RxNormMapping(
                        rxcui=rxcui,
                        name=drug_info.get("name", drug_name),
                        synonym=drug_info.get("synonym"),
                        confidence=0.9  # High confidence for direct RxCUI lookup
                    )
                    mappings.append(mapping)
                else:
                    # Fallback: create basic mapping with RxCUI
                    mapping = RxNormMapping(
                        rxcui=rxcui,
                        name=drug_name,
                        synonym=None,
                        confidence=0.7
                    )
                    mappings.append(mapping)
            
            # If no RxCUIs found, try alternative search methods
            if not mappings:
                # Try to find similar drugs
                alternative_results = self._search_alternative(drug_name, max_results)
                mappings.extend(alternative_results)
            
            logger.info(f"Found {len(mappings)} mappings for {drug_name}")
            return mappings
            
        except Exception as e:
            logger.error(f"Error searching RxNorm for {drug_name}: {e}")
            return []
    
    def _get_drug_info(self, rxcui: str) -> Optional[Dict[str, Any]]:
        """Get detailed drug information from RxCUI"""
        try:
            # Try multiple endpoints to get drug information
            endpoints = [
                f"{self.base_url}/rxcui/{rxcui}/allrelated.json",
                f"{self.base_url}/rxcui/{rxcui}/property.json?propName=RxNorm%20Name",
                f"{self.base_url}/rxcui/{rxcui}/property.json?propName=Display%20Name"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Try to extract name from different response formats
                        if "allRelatedGroup" in data:
                            concept_group = data.get("allRelatedGroup", {}).get("conceptGroup", [])
                            if concept_group:
                                concepts = concept_group[0].get("concept", [])
                                if concepts:
                                    concept = concepts[0]
                                    return {
                                        "name": concept.get("name", ""),
                                        "synonym": concept.get("synonym", ""),
                                        "tty": concept.get("tty", "")
                                    }
                        
                        elif "propValue" in data:
                            return {
                                "name": data.get("propValue", {}).get("value", ""),
                                "synonym": None,
                                "tty": None
                            }
                        
                        elif "displayTerms" in data:
                            terms = data.get("displayTerms", {}).get("term", [])
                            if terms:
                                return {
                                    "name": terms[0].get("name", ""),
                                    "synonym": None,
                                    "tty": None
                                }
                
                except Exception as e:
                    logger.debug(f"Failed to get info from {endpoint}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting drug info for RxCUI {rxcui}: {e}")
            return None
    
    def _search_alternative(self, drug_name: str, max_results: int) -> List[RxNormMapping]:
        """Alternative search method when direct RxCUI lookup fails"""
        try:
            # Try approximate string matching
            url = f"{self.base_url}/drugs.json?name={drug_name}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                drugs = data.get("drugGroup", {}).get("conceptGroup", [])
                
                mappings = []
                for group in drugs[:max_results]:
                    concepts = group.get("concept", [])
                    for concept in concepts:
                        if len(mappings) >= max_results:
                            break
                        
                        mapping = RxNormMapping(
                            rxcui=concept.get("rxcui", ""),
                            name=concept.get("name", drug_name),
                            synonym=concept.get("synonym"),
                            confidence=0.6
                        )
                        mappings.append(mapping)
                
                return mappings
            
            return []
            
        except Exception as e:
            logger.debug(f"Alternative search failed for {drug_name}: {e}")
            return []
    
    def get_drug_interactions(self, rxcuis: List[str]) -> List[DrugInteraction]:
        """Get drug-drug interactions using the correct endpoint"""
        interactions = []
        
        try:
            if len(rxcuis) < 2:
                return interactions
            
            # Use the correct interaction endpoint
            ids = "+".join(rxcuis)
            url = f"{self.base_url}/interaction/list.json?rxcuis={ids}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "interactionTypeGroup" in data:
                groups = data["interactionTypeGroup"]
                if not isinstance(groups, list):
                    groups = [groups]
                
                for group in groups:
                    if "interactionType" in group:
                        interaction_types = group["interactionType"]
                        if not isinstance(interaction_types, list):
                            interaction_types = [interaction_types]
                        
                        for interaction_type in interaction_types:
                            if "interactionPair" in interaction_type:
                                pairs = interaction_type["interactionPair"]
                                if not isinstance(pairs, list):
                                    pairs = [pairs]
                                
                                for pair in pairs:
                                    interaction = self._parse_interaction_pair(pair, rxcuis)
                                    if interaction:
                                        interactions.append(interaction)
            
            return interactions
            
        except Exception as e:
            logger.error(f"Error checking drug interactions: {e}")
            return []
    
    def _parse_interaction_pair(self, pair: Dict[str, Any], rxcuis: List[str]) -> Optional[DrugInteraction]:
        """Parse interaction pair data"""
        try:
            drug1_name = pair.get("interactionConcept", [{}])[0].get("minConceptItem", {}).get("name", "")
            drug2_name = pair.get("interactionConcept", [{}])[1].get("minConceptItem", {}).get("name", "")
            
            severity = "medium"  # Default severity
            description = pair.get("description", "No description available")
            
            # Determine severity based on description keywords
            desc_lower = description.lower()
            if any(word in desc_lower for word in ["severe", "serious", "life-threatening", "contraindicated"]):
                severity = "high"
            elif any(word in desc_lower for word in ["moderate", "moderate"]):
                severity = "medium"
            elif any(word in desc_lower for word in ["mild", "minor", "minimal"]):
                severity = "low"
            
            return DrugInteraction(
                drug1=drug1_name,
                drug2=drug2_name,
                severity=severity,
                description=description,
                recommendation="Consult healthcare provider before combining these medications",
                source="RxNorm"
            )
            
        except Exception as e:
            logger.error(f"Error parsing interaction pair: {e}")
            return None
    
    def check_dosage_safety(self, medication: ExtractedMedication, age: int, weight_kg: float) -> List[SafetyAlert]:
        """Check dosage safety based on patient parameters"""
        alerts = []
        
        try:
            # Basic dosage safety checks
            if age < 18:
                alerts.append(SafetyAlert(
                    severity="medium",
                    message=f"Patient is under 18 years old ({age} years)",
                    recommendation="Verify age-appropriate dosing for this medication",
                    reference="Pediatric dosing guidelines"
                ))
            
            if weight_kg < 30:
                alerts.append(SafetyAlert(
                    severity="medium",
                    message=f"Patient weight is low ({weight_kg} kg)",
                    recommendation="Consider weight-based dosing adjustments",
                    reference="Weight-based dosing guidelines"
                ))
            
            # Check for common high-risk medications
            high_risk_meds = ["warfarin", "digoxin", "insulin", "lithium", "phenytoin"]
            if any(med in medication.drug_name.lower() for med in high_risk_meds):
                alerts.append(SafetyAlert(
                    severity="high",
                    message=f"{medication.drug_name} is a high-risk medication",
                    recommendation="Monitor closely and verify dosing",
                    reference="High-risk medication protocols"
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking dosage safety: {e}")
            return []
    
    def suggest_alternatives(self, medication: ExtractedMedication, allergies: List[str]) -> List[AlternativeMedication]:
        """Suggest alternative medications based on allergies"""
        alternatives = []
        
        try:
            # Check for common allergy cross-reactions
            allergy_alternatives = {
                "penicillin": ["azithromycin", "clindamycin", "doxycycline"],
                "sulfa": ["amoxicillin", "cephalexin", "doxycycline"],
                "aspirin": ["acetaminophen", "ibuprofen", "naproxen"],
                "codeine": ["tramadol", "hydrocodone", "oxycodone"]
            }
            
            for allergy in allergies:
                if allergy.lower() in allergy_alternatives:
                    for alt_drug in allergy_alternatives[allergy.lower()]:
                        alternatives.append(AlternativeMedication(
                            drug_name=alt_drug,
                            reason=f"Alternative to {medication.drug_name} due to {allergy} allergy",
                            strength=medication.strength,
                            route=medication.route,
                            notes="Consult healthcare provider for appropriate dosing"
                        ))
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Error suggesting alternatives: {e}")
            return []


# Global service instance
rxnorm_service = RxNormService()


def get_rxnorm_service() -> RxNormService:
    """Dependency to get RxNorm service instance"""
    return rxnorm_service
