from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union

class TitlePage(BaseModel):
    tender_title: Optional[str] = None
    tender_reference_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    proposal_submitted_by: Optional[str] = None
    submission_date: Optional[str] = None

class Appendix(BaseModel):
    required_documents_checklist: Optional[List[str]] = None
    compliance_certificates: Optional[List[str]] = None
    technical_specifications_summary: Optional[str] = None
    references: Optional[List[str]] = None
    abbreviations_and_glossary: Optional[Dict[str, str]] = None

class Metadata(BaseModel):
    proposal_pages: Optional[str] = None
    word_count: Optional[str] = None
    analysis_date: Optional[str] = None
    tender_type: Optional[str] = None
    estimated_value: Optional[str] = None

class TenderProposalResponse(BaseModel):
    """
    Dynamic response model for government tender proposal
    Sections are flexible based on tender document content
    """
    status: str = Field(default="success", description="Response status")
    message: str = Field(default="Proposal generated successfully")
    generated_at: Optional[str] = Field(default=None, description="Timestamp of generation")
    estimated_pages: Optional[str] = Field(default=None, description="Estimated page count")
    
    # Required core sections
    document_overview: Optional[str] = Field(
        default=None, 
        description="Comprehensive overview of the tender document (800-1000 words)"
    )
    
    title_page: Optional[TitlePage] = Field(
        default=None,
        description="Tender identification information"
    )
    
    executive_summary: Optional[str] = Field(
        default=None,
        description="Executive summary of the proposal (600-800 words)"
    )
    
    # Key points sections (bullet format)
    key_dates_and_rules: Optional[List[str]] = Field(
        default=None,
        description="Important dates, deadlines, and rules in bullet points"
    )
    
    risks_and_gaps: Optional[List[str]] = Field(
        default=None,
        description="Identified risks, gaps, and mitigation strategies in bullet points"
    )
    
    # Descriptive sections (paragraph format)
    compliance_matrix: Optional[str] = Field(
        default=None,
        description="Detailed compliance mapping (500-700 words)"
    )
    
    technical_approach: Optional[str] = Field(
        default=None,
        description="Detailed technical methodology and approach (1000-1200 words)"
    )
    
    financial_proposal_overview: Optional[str] = Field(
        default=None,
        description="Financial approach overview without actual pricing (400-600 words)"
    )
    
    organizational_capability: Optional[str] = Field(
        default=None,
        description="Organization's qualifications and experience (600-800 words)"
    )
    
    recommendations_and_value_additions: Optional[str] = Field(
        default=None,
        description="Recommendations and value-added services (500-700 words)"
    )
    
    implementation_timeline: Optional[str] = Field(
        default=None,
        description="Detailed implementation schedule (400-500 words)"
    )
    
    appendix: Optional[Appendix] = Field(
        default=None,
        description="Supporting information and references"
    )
    
    metadata: Optional[Metadata] = Field(
        default=None,
        description="Proposal metadata and statistics"
    )
    
    # Allow additional dynamic fields
    class Config:
        extra = "allow"  # Allow additional fields for dynamic sections
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Proposal generated successfully",
                "document_overview": "This tender issued by the Department of Public Works seeks...",
                "title_page": {
                    "tender_title": "Supply and Installation of IT Infrastructure",
                    "tender_reference_number": "DPW/IT/2025/001",
                    "issuing_authority": "Department of Public Works",
                    "proposal_submitted_by": "Tech Solutions Ltd.",
                    "submission_date": "2025-11-30"
                },
                "executive_summary": "We are pleased to submit our proposal...",
                "key_dates_and_rules": [
                    "• Tender Publication Date: November 1, 2025",
                    "• Bid Submission Deadline: November 30, 2025, 2:00 PM",
                    "• Mandatory Rule: All bidders must have ISO 9001 certification"
                ],
                "compliance_matrix": "Our organization fully complies with all requirements...",
                "technical_approach": "Our proposed methodology consists of five key phases...",
                "risks_and_gaps": [
                    "• Risk: Tight implementation timeline - Mitigation: Deploy experienced team",
                    "• Gap: Server specifications not fully detailed - Assumption: Industry standard specs"
                ],
                "metadata": {
                    "proposal_pages": "15-20",
                    "word_count": "~11,000 words",
                    "tender_type": "IT Services"
                }
            }
        }

class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = Field(default="error")
    error_type: str = Field(description="Type of error encountered")
    message: str = Field(description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    raw_response: Optional[str] = Field(default=None, description="Raw response for debugging")
    error_details: Optional[str] = Field(default=None, description="Technical error information")
    suggestion: Optional[str] = Field(default=None, description="Suggestion to resolve the error")
    timestamp: Optional[str] = Field(default=None, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error_type": "ValidationError",
                "message": "Invalid PDF file format",
                "details": "The uploaded file does not appear to be a valid PDF",
                "suggestion": "Please ensure you're uploading a valid PDF file"
            }
        }