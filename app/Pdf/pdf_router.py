from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any
import os
from .llm_service import GeminiPDFService
from app.config import settings

router = APIRouter(
    prefix="/pdf",
    tags=["Government Tender Proposal Generation"]
)

# Initialize Gemini service
gemini_service = None

def get_gemini_service():
    """Get or create Gemini service instance"""
    global gemini_service
    if gemini_service is None:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "GEMINI_API_KEY not configured",
                    "message": "Please set GEMINI_API_KEY in your .env file",
                    "instructions": "Add 'GEMINI_API_KEY=your_key_here' to .env file"
                }
            )
        gemini_service = GeminiPDFService(api_key=api_key)
    return gemini_service

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_tender_document(
    file: UploadFile = File(
        ..., 
        description="Government tender PDF document (max 200 pages, 50MB)"
    )
):
    """
    generate a comprehensive 15-20 page proposal.
    
    **Features:**
    - 📄 Analyzes tender documents up to 200 pages
    - 🤖 AI-powered proposal generation using Gemini 2.5 Flash
    - 📊 Dynamic sections based on tender content
    - 📝 10,000-12,000 word comprehensive proposal
    
    **Response Sections:**
    - **Document Overview**: Comprehensive summary of tender (800-1000 words)
    - **Title Page**: Tender identification details
    - **Executive Summary**: Proposal highlights (600-800 words)
    - **Key Dates & Rules**: Bullet points of critical dates and requirements
    - **Compliance Matrix**: Detailed compliance mapping (500-700 words)
    - **Technical Approach**: Implementation methodology (1000-1200 words)
    - **Risks & Gaps**: Bullet points of risks and mitigations
    - **Financial Overview**: Cost approach without pricing (400-600 words)
    - **Organizational Capability**: Company qualifications (600-800 words)
    - **Recommendations**: Value additions (500-700 words)
    - **Implementation Timeline**: Project schedule (400-500 words)
    - **Appendix**: Supporting documents and references
    
    **Returns:** JSON formatted proposal ready for submission
    """
    
    # Validate file type
    if not file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid file type",
                "received": file.content_type,
                "expected": "application/pdf",
                "message": f"Only PDF files are accepted. You uploaded: {file.content_type}"
            }
        )
    
    # Validate file size (50MB max for ~200 pages)
    MAX_FILE_SIZE = settings.MAX_PDF_SIZE_MB * 1024 * 1024
    
    try:
        # Read file content
        pdf_bytes = await file.read()
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        
        # Check file size
        if len(pdf_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "File too large",
                    "file_size": f"{file_size_mb:.2f} MB",
                    "max_size": f"{settings.MAX_PDF_SIZE_MB} MB",
                    "message": f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({settings.MAX_PDF_SIZE_MB} MB)"
                }
            )
        
        # Validate PDF content (basic check for PDF header)
        if not pdf_bytes.startswith(b'%PDF-'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid PDF format",
                    "message": "The uploaded file does not appear to be a valid PDF document",
                    "suggestion": "Please ensure the file is a valid PDF and not corrupted"
                }
            )
        
        # Log processing start
        print(f"[PDF ANALYSIS] Processing tender document: {file.filename} ({file_size_mb:.2f} MB)")
        
        # Get Gemini service
        service = get_gemini_service()
        
        # Generate proposal
        print(f"[PDF ANALYSIS] Generating proposal using {service.model_id}...")
        proposal = service.generate_proposal(pdf_bytes)
        
        # Check if proposal generation was successful
        if proposal.get("status") == "error":
            print(f"[PDF ANALYSIS] Error: {proposal.get('message')}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=proposal
            )
        
        print(f"[PDF ANALYSIS] Proposal generated successfully for {file.filename}")
        print(f"[PDF ANALYSIS] Estimated pages: {proposal.get('estimated_pages', 'N/A')}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=proposal
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PDF ANALYSIS] Exception: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Processing failed",
                "error_type": type(e).__name__,
                "message": str(e),
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )
    finally:
        await file.close()

@router.get("/health")
async def health_check():
    """
    Check if the tender proposal generation service is operational
    
    Returns service status and configuration
    """
    try:
        service = get_gemini_service()
        return {
            "status": "healthy",
            "service": "Government Tender Proposal Generator",
            "model": service.model_id,
            "max_file_size": f"{settings.MAX_PDF_SIZE_MB} MB",
            "max_pages": "~200 pages",
            "output_format": "JSON",
            "estimated_output": "15-20 pages, 10,000-12,000 words",
            "message": "Service is operational and ready to process tender documents"
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "Government Tender Proposal Generator",
                "error": str(e),
                "message": "Service is not properly configured. Please check GEMINI_API_KEY."
            }
        )

@router.get("/info")
async def service_info():
    """
    Get detailed information about the proposal generation service
    """
    return {
        "service_name": "AI-Powered Government Tender Proposal Generator",
        "version": "1.0.0",
        "model": "Google Gemini 2.5 Flash",
        "capabilities": [
            "Government tender document analysis",
            "Comprehensive proposal generation",
            "Dynamic section creation based on tender type",
            "15-20 page detailed proposals",
            "10,000-12,000 word content generation"
        ],
        "input_requirements": {
            "format": "PDF",
            "max_size": f"{settings.MAX_PDF_SIZE_MB} MB",
            "max_pages": "~200 pages",
            "document_type": "Government tender/RFP documents"
        },
        "output_structure": {
            "format": "JSON",
            "sections": [
                "Document Overview (800-1000 words)",
                "Title Page",
                "Executive Summary (600-800 words)",
                "Key Dates & Rules (bullet points)",
                "Compliance Matrix (500-700 words)",
                "Technical Approach (1000-1200 words)",
                "Risks & Gaps (bullet points)",
                "Financial Overview (400-600 words)",
                "Organizational Capability (600-800 words)",
                "Recommendations (500-700 words)",
                "Implementation Timeline (400-500 words)",
                "Appendix"
            ]
        },
        "usage": {
            "endpoint": "/pdf/analyze",
            "method": "POST",
            "content_type": "multipart/form-data",
            "parameter": "file (PDF document)"
        }
    }