from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
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

# Mapping of document categories
DOCUMENT_CATEGORIES = {
    "capability_statement": "Capability Statement",
    "certificate": "Certificate",
    "past_proposal": "Past Proposal",
    "company_profile": "Company Profile",
    "success_story": "Success Story",
    "other": "Other/Supporting Document"
}

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_tender_document(
    tender_file: UploadFile = File(
        ..., 
        description="**REQUIRED**: Main government tender/RFP PDF document (max 200 pages, 50MB)"
    ),
    supporting_documents: Optional[List[UploadFile]] = File(
        None,
        description="**OPTIONAL**: Additional PDF documents to enhance the proposal (Capability Statements, Certificates, Past Proposals, Company Profiles, Success Stories, or other supporting materials). Max 6 files."
    )
):
    """
    Upload a government tender document with optional supporting materials to generate a comprehensive 15-20 page proposal.
    
    **Returns:** JSON formatted proposal ready for submission (10,000-12,000 words, 15-20 pages)
    """
    
    # Validate main tender file
    if not tender_file.content_type == "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid file type for main tender",
                "received": tender_file.content_type,
                "expected": "application/pdf",
                "message": f"Main tender must be a PDF. You uploaded: {tender_file.content_type}"
            }
        )
    
    # Collect all supporting documents
    all_supporting_docs = []
    
    # Process supporting documents if provided
    if supporting_documents:
        for doc in supporting_documents:
            if doc.content_type != "application/pdf":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Invalid file type in supporting documents",
                        "filename": doc.filename,
                        "received": doc.content_type,
                        "expected": "application/pdf",
                        "message": f"All supporting documents must be PDFs. File '{doc.filename}' is {doc.content_type}"
                    }
                )
            
            # Read document bytes
            doc_bytes = await doc.read()
            
            # Auto-detect category based on filename or use generic category
            category = "Supporting Document"
            filename_lower = doc.filename.lower()
            
            if any(word in filename_lower for word in ["capability", "qualification", "strength"]):
                category = "Capability Statement"
            elif any(word in filename_lower for word in ["certificate", "certification", "license", "iso"]):
                category = "Certificate"
            elif any(word in filename_lower for word in ["proposal", "rfp", "tender"]):
                category = "Past Proposal"
            elif any(word in filename_lower for word in ["profile", "company", "organization", "about"]):
                category = "Company Profile"
            elif any(word in filename_lower for word in ["success", "case", "story", "testimonial", "project"]):
                category = "Success Story"
            
            all_supporting_docs.append({
                "bytes": doc_bytes,
                "category": category,
                "filename": doc.filename
            })
        
        await doc.close()
    
    # Validate total number of PDFs (1 tender + supporting docs)
    total_pdfs = 1 + len(all_supporting_docs)
    if total_pdfs > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Too many documents",
                "total_uploaded": total_pdfs,
                "maximum_allowed": 7,
                "message": f"You uploaded {total_pdfs} PDFs. Maximum is 7 (1 tender + 6 supporting documents)",
                "breakdown": {
                    "tender_file": 1,
                    "supporting_documents": len(all_supporting_docs)
                }
            }
        )
    
    # Validate file size
    MAX_FILE_SIZE = settings.MAX_PDF_SIZE_MB * 1024 * 1024
    
    try:
        # Read main tender file
        tender_bytes = await tender_file.read()
        tender_size_mb = len(tender_bytes) / (1024 * 1024)
        
        # Check tender file size
        if len(tender_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "Tender file too large",
                    "file_size": f"{tender_size_mb:.2f} MB",
                    "max_size": f"{settings.MAX_PDF_SIZE_MB} MB",
                    "message": f"Tender file size ({tender_size_mb:.2f} MB) exceeds maximum allowed size ({settings.MAX_PDF_SIZE_MB} MB)"
                }
            )
        
        # Validate tender PDF format
        if not tender_bytes.startswith(b'%PDF-'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid PDF format",
                    "message": "The tender file does not appear to be a valid PDF document",
                    "suggestion": "Please ensure the file is a valid PDF and not corrupted"
                }
            )
        
        # Validate supporting documents size
        for doc in all_supporting_docs:
            doc_size_mb = len(doc['bytes']) / (1024 * 1024)
            if len(doc['bytes']) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "error": "Supporting document too large",
                        "filename": doc['filename'],
                        "category": doc['category'],
                        "file_size": f"{doc_size_mb:.2f} MB",
                        "max_size": f"{settings.MAX_PDF_SIZE_MB} MB"
                    }
                )
        
        # Log processing start
        print(f"[PDF ANALYSIS] Processing tender document: {tender_file.filename} ({tender_size_mb:.2f} MB)")
        if all_supporting_docs:
            print(f"[PDF ANALYSIS] Supporting documents: {len(all_supporting_docs)}")
            for doc in all_supporting_docs:
                doc_size = len(doc['bytes']) / (1024 * 1024)
                print(f"  - {doc['category']}: {doc['filename']} ({doc_size:.2f} MB)")
        
        # Get Gemini service
        service = get_gemini_service()
        
        # Generate proposal
        print(f"[PDF ANALYSIS] Generating proposal using {service.model_id}...")
        proposal = service.generate_proposal(
            tender_pdf_bytes=tender_bytes,
            supporting_docs=all_supporting_docs if all_supporting_docs else None
        )
        
        # Check if proposal generation was successful
        if proposal.get("status") == "error":
            print(f"[PDF ANALYSIS] Error: {proposal.get('message')}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=proposal
            )
        
        print(f"[PDF ANALYSIS] Proposal generated successfully for {tender_file.filename}")
        print(f"[PDF ANALYSIS] Estimated pages: {proposal.get('estimated_pages', 'N/A')}")
        if all_supporting_docs:
            print(f"[PDF ANALYSIS] Enhanced with {len(all_supporting_docs)} supporting documents")
        
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
        await tender_file.close()
        # Close supporting document file handles if needed

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
            "max_pages": "~200 pages per PDF",
            "max_total_pdfs": 7,
            "output_format": "JSON",
            "estimated_output": "15-20 pages, 10,000-12,000 words",
            "supported_document_types": list(DOCUMENT_CATEGORIES.values()),
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
        "version": "2.0.0",
        "model": "Google Gemini 2.5 Flash",
        "capabilities": [
            "Government tender document analysis",
            "Comprehensive proposal generation",
            "Multi-document analysis (tender + supporting docs)",
            "Dynamic section creation based on tender type",
            "15-20 page detailed proposals",
            "10,000-12,000 word content generation"
        ],
        "input_requirements": {
            "tender_document": {
                "required": True,
                "format": "PDF",
                "max_size": f"{settings.MAX_PDF_SIZE_MB} MB",
                "max_pages": "~200 pages",
                "description": "Main government tender/RFP document"
            },
            "supporting_documents": {
                "required": False,
                "max_count": 6,
                "total_max_pdfs": 7,
                "accepted_types": [
                    "Capability Statements",
                    "Certificates and Certifications",
                    "Past Proposals",
                    "Company Profiles",
                    "Success Stories and Case Studies",
                    "Other Supporting Materials"
                ],
                "format": "PDF",
                "max_size_each": f"{settings.MAX_PDF_SIZE_MB} MB",
                "description": "Optional supporting documents uploaded via single field. System auto-detects document type based on filename."
            }
        },
        "output_structure": {
            "format": "JSON",
            "sections": [
                "Document Overview (1000-1200 words)",
                "Title Page",
                "Executive Summary (800-1000 words)",
                "Key Dates & Rules (bullet points)",
                "Compliance Matrix (700-900 words)",
                "Technical Approach (1200-1400 words)",
                "Risks & Gaps (bullet points)",
                "Financial Overview (600-700 words)",
                "Organizational Capability (700-800 words)",
                "Recommendations (700-800 words)",
                "Implementation Timeline (500-600 words)",
                "Appendix"
            ]
        },
        "usage": {
            "endpoint": "/pdf/analyze",
            "method": "POST",
            "content_type": "multipart/form-data",
            "parameters": {
                "tender_file": "Required - Main tender PDF",
                "supporting_documents": "Optional - List of supporting PDFs (any type, max 6 files)"
            },
            "example": "Upload 1 tender PDF + up to 6 supporting PDFs in a single 'supporting_documents' field"
        },
        "enhancement_strategy": {
            "description": "Supporting documents enhance proposal quality through intelligent content extraction",
            "auto_detection": "System automatically detects document type based on filename keywords",
            "integration": {
                "Capability Statements": "Strengthen organizational capability section",
                "Certificates": "Reference in compliance matrix",
                "Past Proposals": "Inform technical methodology",
                "Company Profiles": "Populate company information",
                "Success Stories": "Provide concrete case studies",
                "Supporting Documents": "Integrate relevant context throughout"
            },
            "filename_detection": {
                "capability": ["capability", "qualification", "strength"],
                "certificate": ["certificate", "certification", "license", "iso"],
                "past_proposal": ["proposal", "rfp", "tender"],
                "company_profile": ["profile", "company", "organization", "about"],
                "success_story": ["success", "case", "story", "testimonial", "project"]
            }
        }
    }

@router.get("/document-categories")
async def get_document_categories():
    """
    Get list of supported document categories for supporting materials
    """
    return {
        "categories": DOCUMENT_CATEGORIES,
        "usage_guide": {
            "Capability Statement": "Upload documents showcasing your company's strengths, past performance, and qualifications",
            "Certificate": "Upload relevant certifications, licenses, ISO certificates, and compliance documents",
            "Past Proposal": "Upload previous successful proposals to help inform the technical approach (content will not be copied)",
            "Company Profile": "Upload company brochures, organizational charts, and company overview documents",
            "Success Story": "Upload case studies, project testimonials, and success stories from past work",
            "Other/Supporting Document": "Upload any other relevant supporting materials"
        },
        "best_practices": [
            "Upload only relevant documents that directly support your proposal",
            "Ensure all certificates are current and valid",
            "Past proposals should be from similar project types",
            "Company profiles should be recent and accurate",
            "Success stories should demonstrate relevant experience",
            "Maximum 6 supporting documents across all categories"
        ]
    }