"""
Translation service to support English → Tamil translations using Hugging Face models.
Falls back to working models if custom model is unavailable.
"""

from typing import Optional
import logging

from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)
import torch

logger = logging.getLogger(__name__)


class TranslationService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.mode = "none"
        self._granite_client = None
        self._settings = None

        # First, try IBM Granite via watsonx if configured
        if self._try_init_granite():
            self.mode = "granite"
            logger.info("Using IBM Granite translation via watsonx.ai")
            return

        # Try working English→Tamil models
        working_models = [
            "Helsinki-NLP/opus-mt-en-ta",
            "facebook/nllb-200-distilled-600M",
            "facebook/nllb-200-1.3B"
        ]
        
        for model_id in working_models:
            try:
                logger.info(f"Loading translation model: {model_id}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_id)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
                self.model.to(self.device)
                self.mode = "huggingface"
                logger.info(f"Loaded translation model {model_id} successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to load model '{model_id}': {e}")
                continue

        # If all models fail, log error
        logger.error("Failed to load any translation model")
        self.model = None
        self.tokenizer = None
        self.mode = "none"

    def translate_en_to_ta(self, text: str) -> str:
        if not text or not text.strip():
            return text

        try:
            if self.mode == "granite":
                return self._translate_with_granite(text)

            if self.mode == "huggingface" and self.model and self.tokenizer:
                # Handle different model types
                if "nllb" in self.tokenizer.name_or_path:
                    # NLLB models use language codes
                    encoded = self.tokenizer(text, return_tensors="pt").to(self.device)
                    generated = self.model.generate(
                        **encoded,
                        forced_bos_token_id=self.tokenizer.lang_code_to_id["tam_Taml"],
                        max_new_tokens=512,
                    )
                else:
                    # Standard sequence-to-sequence models
                    encoded = self.tokenizer(text, return_tensors="pt").to(self.device)
                    generated = self.model.generate(**encoded, max_new_tokens=512)
                
                translated = self.tokenizer.decode(generated[0], skip_special_tokens=True)
                logger.info(f"Translation: '{text}' -> '{translated}'")
                return translated
            
            # Fallback to simple dictionary translation
            return self._simple_fallback_translation(text)

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Fallback to simple dictionary translation
            return self._simple_fallback_translation(text)
    
    def _simple_fallback_translation(self, text: str) -> str:
        """Simple fallback translation using common medical terms dictionary"""
        # Common medical terms in English -> Tamil
        medical_terms = {
            "medications": "மருந்துகள்",
            "aspirin": "ஆஸ்பிரின்",
            "oxycodone": "ஆக்சிகோடோன்",
            "diazepam": "டயாசெபாம்",
            "paracetamol": "பாராசிட்டமோல்",
            "acetaminophen": "அசிட்டமினோஃபென்",
            "ibuprofen": "ஐபுப்ரோஃபென்",
            "penicillin": "பெனிசிலின்",
            "amoxicillin": "அமோக்சிசிலின்",
            "warfarin": "வார்ஃபரின்",
            "insulin": "இன்சுலின்",
            "metformin": "மெட்ஃபார்மின்",
            "daily": "தினசரி",
            "twice": "இருமுறை",
            "three times": "மூன்று முறை",
            "as needed": "தேவைக்கேற்ப",
            "for": "க்கு",
            "days": "நாட்கள்",
            "weeks": "வாரங்கள்",
            "months": "மாதங்கள்",
            "mg": "மி.கி",
            "mcg": "மைக்ரோகிராம்",
            "g": "கிராம்",
            "ml": "மில்லி லிட்டர்",
            "units": "அலகுகள்",
            "tablet": "மாத்திரை",
            "capsule": "காப்சூல்",
            "injection": "ஊசி",
            "oral": "வாய்வழி",
            "intravenous": "சிரைவழி",
            "intramuscular": "தசைவழி",
            "subcutaneous": "தோலடி",
            "topical": "மேற்புற",
            "inhalation": "உள்ளிழுப்பு",
            "alerts": "எச்சரிக்கைகள்",
            "interactions": "ஊடாடல்கள்",
            "severe": "கடுமையான",
            "moderate": "மிதமான",
            "mild": "லேசான",
            "high": "உயர்ந்த",
            "medium": "நடுத்தர",
            "low": "குறைந்த",
            "recommendation": "பரிந்துரை",
            "consult": "ஆலோசிக்கவும்",
            "healthcare": "சுகாதார",
            "provider": "வழங்குநர்",
            "before": "முன்",
            "combining": "இணைப்பதற்கு",
            "these": "இந்த",
            "drugs": "மருந்துகள்",
            "no": "இல்லை",
            "data": "தரவு",
            "found": "கண்டுபிடிக்கப்பட்டது",
            "results": "முடிவுகள்",
            "search": "தேடல்",
            "database": "தரவுத்தளம்",
            "drug": "மருந்து",
            "name": "பெயர்",
            "strength": "வலிமை",
            "frequency": "அதிர்வெண்",
            "duration": "காலம்",
            "route": "வழி",
            "confidence": "நம்பிக்கை",
            "synonym": "பரியாயம்",
            "rxcui": "ஆர்.எக்ஸ்.சி.யூ.ஐ",
            "alternative": "மாற்று",
            "reason": "காரணம்",
            "notes": "குறிப்புகள்"
        }
        
        # Simple word-by-word translation
        translated_words = []
        words = text.lower().split()
        
        for word in words:
            # Clean word (remove punctuation)
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in medical_terms:
                translated_words.append(medical_terms[clean_word])
            else:
                # Keep original word if no translation found
                translated_words.append(word)
        
        result = " ".join(translated_words)
        logger.info(f"Fallback translation: '{text}' -> '{result}'")
        return result

    def _try_init_granite(self) -> bool:
        """Initialize IBM watsonx.ai Granite client if environment is configured.
        Returns True on success, False otherwise.
        """
        try:
            # Lazy import so environments without watsonx SDK still work
            from app.core.config import get_settings
            self._settings = get_settings()

            if not (
                self._settings.watsonx_url
                and self._settings.watsonx_api_key
                and self._settings.watsonx_project_id
            ):
                return False

            try:
                # Prefer official ibm-watsonx-ai SDK if available
                from ibm_watsonx_ai import Credentials
                from ibm_watsonx_ai.foundation_models import Model

                creds = Credentials(
                    api_key=self._settings.watsonx_api_key,
                    url=self._settings.watsonx_url,
                )
                self._granite_client = Model(
                    model_id=self._settings.granite_model_id or "ibm/granite-13b-instruct-v2",
                    credentials=creds,
                    project_id=self._settings.watsonx_project_id,
                    params={
                        "temperature": self._settings.granite_temperature,
                        "max_new_tokens": self._settings.granite_max_new_tokens,
                    },
                )
                return True
            except Exception as e:
                logger.warning(f"watsonx SDK not available or failed to init Granite: {e}")
                return False
        except Exception as e:
            logger.debug(f"Granite init skipped: {e}")
            return False

    def _translate_with_granite(self, text: str) -> str:
        """Translate English to Tamil using Granite via instruction prompting."""
        if not self._granite_client:
            return text

        system_prompt = (
            "You are a professional translator. Translate the following English text to Tamil. "
            "Only return the translation, without quotes or extra commentary."
        )
        prompt = f"{system_prompt}\n\nEnglish: {text}\nTamil:"

        try:
            # The SDK's generate method returns a dict with 'results' typically
            response = self._granite_client.generate(prompt=prompt)
            if isinstance(response, dict):
                # try common shapes
                if "results" in response and response["results"]:
                    return (response["results"][0].get("generated_text") or text).strip()
                if "generated_text" in response:
                    return (response.get("generated_text") or text).strip()
            # Some SDK versions return a string directly
            if isinstance(response, str):
                return response.strip()
        except Exception as e:
            logger.error(f"Granite translation failed: {e}")
        return text


# Global instance and dependency helper
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


