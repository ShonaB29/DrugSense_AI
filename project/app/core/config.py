"""
Configuration settings for the Prescription Authenticator AI system
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application Configuration
    app_name: str = "Prescription Authenticator AI"
    app_version: str = "1.0.0"
    debug: bool = True

    # JWT Configuration
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # RxNorm API Configuration
    rxnorm_api_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    rxnorm_timeout: int = 10

    # Hugging Face Configuration
    hf_model_name: str = "d4data/biomedical-ner-all"
    hf_cache_dir: str = "./models_cache"
    hf_use_auth_token: Optional[str] = None

    # IBM watsonx / Granite Configuration (optional; enables Granite translation when set)
    watsonx_url: Optional[str] = None
    watsonx_api_key: Optional[str] = None
    watsonx_project_id: Optional[str] = None
    granite_model_id: Optional[str] = "ibm/granite-13b-instruct-v2"
    granite_temperature: float = 0.2
    granite_max_new_tokens: int = 256

    # CORS Configuration
    allowed_origins: List[str] = [
        "http://localhost:8501",  # Streamlit default
        "http://localhost:3000",  # React default
        "http://127.0.0.1:8501",
        "http://127.0.0.1:3000",
    ]

    # Database Configuration (for future use)
    database_url: Optional[str] = None

    # OCR Configuration
    tesseract_cmd: Optional[str] = None

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Performance Configuration
    max_text_length: int = 10000
    max_image_size_mb: int = 10
    request_timeout: int = 30

    # Security Configuration
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Ensure cache directory exists
        cache_path = Path(self.hf_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        # Set Tesseract path if not provided
        if not self.tesseract_cmd:
            self.tesseract_cmd = self._find_tesseract()

    def _find_tesseract(self) -> Optional[str]:
        """Find Tesseract executable path"""
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        # Try to find in PATH
        import shutil

        return shutil.which("tesseract")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.debug

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global _settings
    _settings = Settings()
    return _settings
