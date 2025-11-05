from google import genai
from google.genai.types import Part
import json
from typing import Dict, Any
import os
from datetime import datetime

class GeminiPDFService:
    def __init__(self, api_key: str):
        """Initialize Gemini client with API key"""
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash"
        
    def generate_proposal(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analyze government tender PDF and generate a comprehensive proposal
        
        Args:
            pdf_bytes: PDF file content in bytes
            
        Returns:
            Dict containing the generated proposal in JSON format
        """
        prompt = """
You are an expert government tender analyst and proposal writer. 
Analyze the provided government tender document and create a comprehensive, professional proposal response.

IMPORTANT: You MUST respond in valid JSON format with a dynamic structure based on the tender document content.

Your response should follow this structure:
{
    "document_overview": "A comprehensive 1000-1200 word overview that summarizes the entire tender document. This should give readers a complete understanding of: the tendering organization, project scope, objectives, budget range, evaluation criteria, and overall requirements. Make this section detailed and informative.",
    
    "title_page": {
        "tender_title": "Extract the exact tender/project title",
        "tender_reference_number": "Tender/RFP reference number",
        "issuing_authority": "Government department/organization issuing the tender",
        "proposal_submitted_by": "Your organization name (can be placeholder like 'Bidding Organization')",
        "submission_date": "Today's date or deadline date"
    },
    
    "executive_summary": "Write a compelling 800-1000 word executive summary that: highlights your understanding of the tender requirements, outlines your proposed solution approach, emphasizes your key strengths and differentiators, summarizes expected outcomes and benefits. Make this persuasive and professional.",
    
    "key_dates_and_rules": [
        "• Tender Publication Date: [Date]",
        "• Pre-bid Meeting: [Date and details if mentioned]",
        "• Deadline for Queries: [Date]",
        "• Bid Submission Deadline: [Date and time]",
        "• Technical Evaluation Period: [Timeframe]",
        "• Expected Award Date: [Date]",
        "• Project Start Date: [Date]",
        "• Mandatory Rule: [Rule description]",
        "• Eligibility Criteria: [Criteria]",
        "• Submission Format: [Requirements]",
        "• EMD/Bid Security: [Amount and details]",
        "• Performance Guarantee: [Percentage/amount]"
    ],
    
    "compliance_matrix": "Write a detailed 700-900 word section that: maps each tender requirement to your proposed solution, demonstrates how you meet technical specifications, shows compliance with eligibility criteria, addresses evaluation parameters, highlights certifications and qualifications. Use descriptive paragraphs, not bullet points.",
    
    "technical_approach": "Provide a comprehensive 1200-1400 word description of: your proposed methodology, implementation strategy, technical architecture (if applicable), resource allocation plan, quality assurance measures, risk management approach, timeline and milestones. Be detailed and specific.",
    
    "risks_and_gaps": [
        "• Risk: [Identified risk from tender analysis]",
        "• Gap: [Any missing information or unclear requirement]",
        "• Challenge: [Potential implementation challenge]",
        "• Mitigation: [Your proposed mitigation strategy]",
        "• Assumption: [Any assumptions made due to unclear requirements]"
    ],
    
    "financial_proposal_overview": "Write a 600-700 word overview covering: cost structure approach, pricing methodology, value for money justification, payment terms understanding, budget optimization strategies. Do NOT include actual prices (those come in separate financial bid).",
    
    "organizational_capability": "Provide 700-800 words describing: your organization's experience with similar projects, relevant case studies, team qualifications, infrastructure and resources, certifications and accreditations, past performance with government projects.",
    
    "recommendations_and_value_additions": "Write 700-800 words detailing: innovative solutions beyond basic requirements, value-added services, sustainability considerations, long-term benefits, post-implementation support, continuous improvement suggestions.",
    
    "implementation_timeline": "Provide a detailed 500-600 word description of: project phases, key milestones, deliverable schedule, resource deployment plan, quality checkpoints, testing and acceptance procedures.",
    
    "appendix": {
        "required_documents_checklist": ["List of all documents mentioned in tender that need to be attached"],
        "compliance_certificates": ["Certifications required"],
        "technical_specifications_summary": "Brief summary of key technical specs",
        "references": ["Any standards, regulations, or documents referenced"],
        "abbreviations_and_glossary": {"Term": "Definition of technical terms used"}
    },
    
    "metadata": {
        "proposal_pages": "15-20",
        "word_count": "Approximately 10,000-12,000 words",
        "analysis_date": "Current date",
        "tender_type": "Identified tender category (e.g., IT Services, Construction, Consulting)",
        "estimated_value": "Tender value if mentioned"
    }
}

CRITICAL INSTRUCTIONS:
1. **Dynamic Headlines**: Create section headings based on the actual tender content. If the tender is for IT services, use IT-specific sections. If construction, use construction-specific sections.

2. **Key Dates and Rules**: Present as bullet points (•) with clear, concise information. Include dates, amounts, and requirements.

3. **Risks and Gaps**: Present as bullet points (•) highlighting specific concerns and mitigation strategies.

4. **All Other Sections**: Write in detailed, descriptive paragraphs. Be comprehensive and professional.

5. **Document Overview**: This is crucial - make it detailed enough that someone reading only this section understands the complete tender.

6. **Word Count**: Aim for 10,000-12,000 total words to ensure 15-20 pages of content.

7. **Professional Tone**: Use formal business language appropriate for government proposals.

8. **Specificity**: Base everything on the actual tender document. Extract real dates, numbers, requirements.

9. **Valid JSON**: Ensure your response is properly formatted JSON that can be parsed.

10. **Completeness**: Fill all sections with meaningful content. Never use placeholders like "TBD" or "Not specified" - instead write what would be typical or expected based on the tender context.

Now analyze the provided tender document and generate a complete, professional proposal.
"""

        try:
            # Create PDF part from bytes
            pdf_file = Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            )
            
            # Generate content using Gemini
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[pdf_file, prompt],
            )
            
            # Parse response text as JSON
            report_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if report_text.startswith("```json"):
                report_text = report_text[7:]
            if report_text.startswith("```"):
                report_text = report_text[3:]
            if report_text.endswith("```"):
                report_text = report_text[:-3]
            
            report_text = report_text.strip()
            
            # Parse JSON
            try:
                proposal_data = json.loads(report_text)
            except json.JSONDecodeError as je:
                # If JSON parsing fails, return structured error with raw text
                return {
                    "status": "error",
                    "error_type": "json_parse_error",
                    "message": "Failed to parse AI response as JSON. The model may have generated text instead of JSON format.",
                    "raw_response": report_text[:2000],  # First 2000 chars for debugging
                    "error_details": str(je),
                    "suggestion": "Try uploading the PDF again or check if the PDF is readable"
                }
            
            # Add success status and timestamp
            proposal_data["status"] = "success"
            proposal_data["message"] = "Proposal generated successfully"
            proposal_data["generated_at"] = datetime.now().isoformat()
            
            # Calculate approximate page count based on word count
            total_words = sum(
                len(str(v).split()) for v in proposal_data.values() 
                if isinstance(v, (str, list))
            )
            proposal_data["estimated_pages"] = f"{max(15, min(20, total_words // 600))}-{max(16, min(20, total_words // 500))} pages"
            
            return proposal_data
            
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "message": f"Error generating proposal: {str(e)}",
                "details": "Failed to process tender document. Please ensure the PDF is valid and readable.",
                "timestamp": datetime.now().isoformat()
            }