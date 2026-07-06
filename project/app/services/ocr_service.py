"""
OCR service for extracting text from prescription images
"""

import logging
from typing import Optional, Tuple
import cv2
import numpy as np
from PIL import Image
import io
import base64

# OCR imports with fallback
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

logger = logging.getLogger(__name__)


class OCRService:
    """OCR service for prescription image text extraction"""
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.easyocr_available = EASYOCR_AVAILABLE
        self.easyocr_reader = None
        
        if self.easyocr_available:
            try:
                self.easyocr_reader = easyocr.Reader(['en'])
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                self.easyocr_available = False
    
    def extract_text_from_image(self, image_data: str, image_format: str = "png") -> Tuple[str, float]:
        """Extract text from base64 encoded image data"""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Try different OCR methods
            text, confidence = self._extract_with_easyocr(processed_image)
            if text and confidence > 0.5:
                return text, confidence
            
            text, confidence = self._extract_with_tesseract(processed_image)
            if text and confidence > 0.3:
                return text, confidence
            
            # Fallback to basic extraction
            return self._extract_basic_text(processed_image)
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return "", 0.0
    
    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Convert to grayscale if needed
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply preprocessing techniques
            # 1. Resize for better OCR
            height, width = gray.shape
            if width < 800:
                scale = 800 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 2. Denoise
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # 3. Enhance contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # 4. Binarization
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return np.array(image)
    
    def _extract_with_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using EasyOCR"""
        if not self.easyocr_available or not self.easyocr_reader:
            return "", 0.0
        
        try:
            results = self.easyocr_reader.readtext(image)
            
            if not results:
                return "", 0.0
            
            # Combine all detected text
            text_parts = []
            total_confidence = 0.0
            
            for (bbox, text, confidence) in results:
                if text.strip() and confidence > 0.3:
                    text_parts.append(text.strip())
                    total_confidence += confidence
            
            if text_parts:
                combined_text = " ".join(text_parts)
                avg_confidence = total_confidence / len(text_parts)
                return combined_text, avg_confidence
            
            return "", 0.0
            
        except Exception as e:
            logger.error(f"Error with EasyOCR: {e}")
            return "", 0.0
    
    def _extract_with_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
        """Extract text using Tesseract"""
        if not self.tesseract_available:
            return "", 0.0
        
        try:
            # Configure Tesseract for medical text
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\s\-\.\/\(\)\:'
            
            text = pytesseract.image_to_string(image, config=custom_config)
            
            if text.strip():
                # Calculate confidence based on text quality
                confidence = self._calculate_text_confidence(text)
                return text.strip(), confidence
            
            return "", 0.0
            
        except Exception as e:
            logger.error(f"Error with Tesseract: {e}")
            return "", 0.0
    
    def _extract_basic_text(self, image: np.ndarray) -> Tuple[str, float]:
        """Basic text extraction fallback"""
        try:
            # Simple edge detection and text region identification
            edges = cv2.Canny(image, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Extract text from regions
            text_regions = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > 50 and h > 20:  # Filter small regions
                    roi = image[y:y+h, x:x+w]
                    # Try to extract text from this region
                    if self.tesseract_available:
                        try:
                            region_text = pytesseract.image_to_string(roi, config='--psm 8')
                            if region_text.strip():
                                text_regions.append(region_text.strip())
                        except:
                            pass
            
            if text_regions:
                combined_text = " ".join(text_regions)
                return combined_text, 0.2  # Low confidence for basic extraction
            
            return "", 0.0
            
        except Exception as e:
            logger.error(f"Error in basic text extraction: {e}")
            return "", 0.0
    
    def _calculate_text_confidence(self, text: str) -> float:
        """Calculate confidence score based on text quality"""
        if not text.strip():
            return 0.0
        
        # Check for medical terms and prescription patterns
        medical_terms = ['mg', 'mcg', 'g', 'ml', 'units', 'tablet', 'capsule', 'injection']
        prescription_patterns = ['daily', 'twice', 'three times', 'as needed', 'for']
        
        confidence = 0.3  # Base confidence
        
        # Increase confidence for medical terms
        text_lower = text.lower()
        for term in medical_terms:
            if term in text_lower:
                confidence += 0.1
        
        # Increase confidence for prescription patterns
        for pattern in prescription_patterns:
            if pattern in text_lower:
                confidence += 0.05
        
        # Increase confidence for numbers (doses)
        if any(char.isdigit() for char in text):
            confidence += 0.1
        
        # Increase confidence for proper formatting
        if len(text.split()) > 3:
            confidence += 0.1
        
        return min(confidence, 0.9)  # Cap at 0.9
