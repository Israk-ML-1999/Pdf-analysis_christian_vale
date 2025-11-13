import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        
        # Validate critical API keys
        self._validate_api_keys()

    # ══════════════════════════════════════════════════════════════
    # App Configuration 
    # ══════════════════════════════════════════════════════════════
    APP_NAME: str = "Government Tender Proposal Generator API"
    APP_DESCRIPTION: str = "AI-powered tender analysis and proposal generation system"
    APP_VERSION: str = "1.0.0"
    
    # ══════════════════════════════════════════════════════════════
    # OpenAI Configuration (for voice assistant features)
    # ══════════════════════════════════════════════════════════════
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    CHAT_MODEL: str = "gpt-4-1-mini"
    
    # ══════════════════════════════════════════════════════════════
    # Google Gemini Configuration (for PDF analysis)
    # ══════════════════════════════════════════════════════════════
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_API_ENDPOINT: str = "https://generativelanguage.googleapis.com"
    
    # ══════════════════════════════════════════════════════════════
    # PDF Processing Configuration
    # ══════════════════════════════════════════════════════════════
    MAX_PDF_SIZE_MB: int = 50  # Maximum PDF file size in MB
    MAX_PDF_PAGES: int = 200   # Maximum number of pages to process
    ALLOWED_FILE_TYPES: list = ["application/pdf"]
    
    # Proposal Generation Settings
    MIN_PROPOSAL_WORDS: int = 10000  # Minimum words in generated proposal
    MAX_PROPOSAL_WORDS: int = 12000  # Maximum words in generated proposal
    TARGET_PROPOSAL_PAGES: str = "15-20"  # Target page count for proposal
    
    # ══════════════════════════════════════════════════════════════
    # Model Configuration (OpenAI)
    # ══════════════════════════════════════════════════════════════
    MAX_TOKENS: int = 1000
    TEMPERATURE: float = 0.7
    MAX_HISTORY_MESSAGES: int = 5
    
    # ══════════════════════════════════════════════════════════════
    # Logging Configuration
    # ══════════════════════════════════════════════════════════════
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DEBUG_LOGS: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # ══════════════════════════════════════════════════════════════
    # Timeout Configuration
    # ══════════════════════════════════════════════════════════════
    PDF_PROCESSING_TIMEOUT: int = 300  # 5 minutes timeout for PDF processing
    API_REQUEST_TIMEOUT: int = 120   # 1 minute timeout for API requests
    
    # ══════════════════════════════════════════════════════════════
    # Rate Limiting (optional)
    # ══════════════════════════════════════════════════════════════
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "False").lower() == "true"
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10"))
    
    # ══════════════════════════════════════════════════════════════
    # Tender Document Types (for dynamic section generation)
    # ══════════════════════════════════════════════════════════════
    SUPPORTED_TENDER_TYPES: list = [
        "IT Services",
        "Construction",
        "Consulting",
        "Supply & Procurement",
        "Infrastructure",
        "Healthcare",
        "Education",
        "Transportation",
        "General Services"
    ]
    
    # ══════════════════════════════════════════════════════════════
    # Proposal Sections Configuration
    # ══════════════════════════════════════════════════════════════
    PROPOSAL_SECTIONS: Dict[str, Dict[str, Any]] = {
        "document_overview": {
            "required": True,
            "format": "descriptive",
            "word_count": "1000-1200",
            "description": "Comprehensive summary of tender document"
        },
        "title_page": {
            "required": True,
            "format": "structured",
            "description": "Tender identification information"
        },
        "executive_summary": {
            "required": True,
            "format": "descriptive",
            "word_count": "800-1000",
            "description": "High-level proposal overview"
        },
        "key_dates_and_rules": {
            "required": True,
            "format": "bullet_points",
            "description": "Critical dates and requirements"
        },
        "compliance_matrix": {
            "required": True,
            "format": "descriptive",
            "word_count": "700-900",
            "description": "Requirement compliance mapping"
        },
        "technical_approach": {
            "required": True,
            "format": "descriptive",
            "word_count": "1200-1400",
            "description": "Implementation methodology"
        },
        "risks_and_gaps": {
            "required": True,
            "format": "bullet_points",
            "description": "Risk analysis and mitigation"
        },
        "financial_proposal_overview": {
            "required": True,
            "format": "descriptive",
            "word_count": "600-700",
            "description": "Cost approach overview"
        },
        "organizational_capability": {
            "required": True,
            "format": "descriptive",
            "word_count": "700-800",
            "description": "Company qualifications"
        },
        "recommendations_and_value_additions": {
            "required": True,
            "format": "descriptive",
            "word_count": "700-800",
            "description": "Value-added services"
        },
        "implementation_timeline": {
            "required": True,
            "format": "descriptive",
            "word_count": "500-600",
            "description": "Project schedule"
        },
        "appendix": {
            "required": True,
            "format": "structured",
            "description": "Supporting documents"
        }
    }
    
    # ══════════════════════════════════════════════════════════════
    # Private Methods
    # ══════════════════════════════════════════════════════════════
    def _validate_api_keys(self):
        """Validate that critical API keys are configured"""
        warnings = []
        
        if not self.GEMINI_API_KEY:
            warnings.append("⚠️  GEMINI_API_KEY not set - PDF analysis will not work")
        
        if not self.OPENAI_API_KEY:
            warnings.append("⚠️  OPENAI_API_KEY not set - Voice assistant features disabled")
        
        if warnings:
            print("\n" + "="*60)
            print("CONFIGURATION WARNINGS:")
            for warning in warnings:
                print(f"  {warning}")
            print("="*60 + "\n")
    
    # ══════════════════════════════════════════════════════════════
    # Helper Methods
    # ══════════════════════════════════════════════════════════════
    def get_max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes"""
        return self.MAX_PDF_SIZE_MB * 1024 * 1024
    
    def is_file_type_allowed(self, content_type: str) -> bool:
        """Check if file type is allowed"""
        return content_type in self.ALLOWED_FILE_TYPES
    
    def get_proposal_word_range(self) -> tuple:
        """Get min and max word count for proposals"""
        return (self.MIN_PROPOSAL_WORDS, self.MAX_PROPOSAL_WORDS)
    
    def __post_init__(self):
        """Post-initialization validation (if needed)"""
        pass

# Create settings instance
settings = Settings()

# Print configuration summary on startup
if settings.ENABLE_DEBUG_LOGS:
    print("\n" + "="*60)
    print("APPLICATION CONFIGURATION")
    print("="*60)
    print(f"App Name: {settings.APP_NAME}")
    print(f"Version: {settings.APP_VERSION}")
    print(f"Gemini Model: {settings.GEMINI_MODEL}")
    print(f"Max PDF Size: {settings.MAX_PDF_SIZE_MB} MB")
    print(f"Max Pages: {settings.MAX_PDF_PAGES}")
    print(f"Target Proposal: {settings.TARGET_PROPOSAL_PAGES} pages")
    print(f"Word Count Range: {settings.MIN_PROPOSAL_WORDS}-{settings.MAX_PROPOSAL_WORDS}")
    print("="*60 + "\n")