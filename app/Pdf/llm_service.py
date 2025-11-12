from google import genai
from google.genai.types import Part
import json
import re
from typing import Dict, Any
import os
from datetime import datetime

class GeminiPDFService:
    def __init__(self, api_key: str):
        """Initialize Gemini client with API key"""
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.5-flash"
        
    def _clean_json_string(self, text: str) -> str:
        """
        Clean and prepare text for JSON parsing
        Handles control characters, markdown blocks, and malformed JSON
        """
        # Remove markdown code block wrappers
        text = text.strip()
        
        # Remove various markdown patterns
        if text.startswith("```json"):
            text = text[7:].strip()
        elif text.startswith("```"):
            text = text[3:].strip()
        
        if text.endswith("```"):
            text = text[:-3].strip()
        
        # Remove control characters except \n, \r, \t (which are valid in JSON strings when escaped)
        # This includes null bytes and other problematic characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Try to find JSON object boundaries
        # Sometimes the model generates text before or after the JSON
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text = text[start_idx:end_idx + 1]
        
        return text.strip()
    
    def _parse_json_safely(self, text: str) -> Dict[str, Any]:
        """
        Attempt to parse JSON with multiple strategies
        Handles markdown, control chars, escaped newlines, truncation
        """
        # Strategy 1: Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[JSON PARSE] Direct parse failed at position {e.pos}: {e.msg}")
        
        # Strategy 2: Clean and parse
        try:
            cleaned = self._clean_json_string(text)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[JSON PARSE] Cleaned parse failed at position {e.pos}: {e.msg}")
        
        # Strategy 3: Fix escaped newlines in string literals
        try:
            cleaned = self._clean_json_string(text)
            # Replace actual newlines with \\n within strings
            # This is a careful regex that handles quoted strings
            fixed = re.sub(
                r'"([^"\\]|\\.)*"',
                lambda m: m.group(0).replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t'),
                cleaned,
                flags=re.MULTILINE | re.DOTALL
            )
            return json.loads(fixed)
        except Exception as e:
            print(f"[JSON PARSE] Escaped newlines fix failed: {e}")
        
        # Strategy 4: Try to close incomplete JSON (if response was cut off)
        try:
            cleaned = self._clean_json_string(text)
            # Count braces to see if JSON is incomplete
            open_braces = cleaned.count('{') - cleaned.count('}')
            open_brackets = cleaned.count('[') - cleaned.count(']')
            
            if open_braces > 0 or open_brackets > 0:
                print(f"[JSON PARSE] Detected incomplete JSON: {open_braces} unclosed braces, {open_brackets} unclosed brackets. Attempting to close...")
                # Close open structures
                fixed = cleaned + ('}' * open_braces) + (']' * open_brackets)
                result = json.loads(fixed)
                print(f"[JSON PARSE] Successfully parsed truncated JSON after closing structures")
                return result
        except Exception as e:
            print(f"[JSON PARSE] Truncation fix failed: {e}")
        
        # Strategy 5: Extract and merge multiple JSON objects (if multiple were generated)
        try:
            cleaned = self._clean_json_string(text)
            # Find all JSON objects
            json_objects = []
            depth = 0
            current_obj = ""
            
            for char in cleaned:
                current_obj += char
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0 and current_obj.strip():
                        try:
                            obj = json.loads(current_obj)
                            json_objects.append(obj)
                            current_obj = ""
                        except:
                            pass
            
            if len(json_objects) > 0:
                print(f"[JSON PARSE] Found {len(json_objects)} JSON objects, merging...")
                merged = {}
                for obj in json_objects:
                    merged.update(obj)
                return merged
        except Exception as e:
            print(f"[JSON PARSE] Multiple JSON merge failed: {e}")
        
        # Last resort - return structured error
        raise ValueError("All JSON parsing strategies failed")
        
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

CRITICAL: Your ENTIRE response must be ONLY valid JSON - NO markdown formatting, NO code blocks, NO explanatory text.
Do NOT wrap your response in ```json or ``` or any markdown.
Output ONLY the raw JSON object, nothing else.

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
1. **ONLY JSON OUTPUT**: Your response must be ONLY valid JSON. No markdown. No code blocks. No text outside the JSON object.
2. **Dynamic Headlines**: Create section headings based on the actual tender content. If the tender is for IT services, use IT-specific sections. If construction, use construction-specific sections.
3. **Key Dates and Rules**: Present as array items with clear, concise information. Include dates, amounts, and requirements.
4. **Risks and Gaps**: Present as array items highlighting specific concerns and mitigation strategies.
5. **All Other Sections**: Write in detailed, descriptive paragraphs. Be comprehensive and professional.
6. **Document Overview**: This is crucial - make it detailed enough that someone reading only this section understands the complete tender.
7. **Word Count**: Aim for 10,000-12,000 total words to ensure 15-20 pages of content.
8. **Professional Tone**: Use formal business language appropriate for government proposals.
9. **Specificity**: Base everything on the actual tender document. Extract real dates, numbers, requirements.
10. **Valid JSON**: Ensure your response is properly formatted JSON. Use proper escaping for special characters (\\n for newlines, \\" for quotes, etc).
11. **Completeness**: Fill all sections with meaningful content. Never use placeholders like "TBD" or "Not specified" - instead write what would be typical or expected based on the tender context.
12. **DO NOT include markdown code blocks or triple backticks**: Just output the raw JSON object starting with { and ending with }.

Now analyze the provided tender document and generate ONLY a complete, professional proposal JSON object with no other text.
"""

        try:
            # Create PDF part from bytes
            pdf_file = Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            )
            
            # Generate content using Gemini
            print(f"[GEMINI] Sending request to {self.model_id}...")
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[pdf_file, prompt],
            )
            
            print(f"[GEMINI] Response received, parsing JSON...")
            
            # Get response text
            report_text = response.text.strip()
            
            # Log first 500 chars for debugging
            print(f"[GEMINI] Response preview: {report_text[:500]}...")
            
            # Parse JSON with multiple strategies
            try:
                proposal_data = self._parse_json_safely(report_text)
            except ValueError as ve:
                # All parsing strategies failed
                return {
                    "status": "error",
                    "error_type": "json_parse_error",
                    "message": "Failed to parse AI response as valid JSON after multiple attempts.",
                    "raw_response": report_text[:2000],
                    "error_details": str(ve),
                    "suggestion": "The AI model generated malformed JSON. Please try again or use a smaller PDF.",
                    "debug_info": {
                        "response_length": len(report_text),
                        "starts_with": report_text[:100],
                        "ends_with": report_text[-100:]
                    }
                }
            
            # Validate required fields
            required_fields = [
                "document_overview", "title_page", "executive_summary",
                "key_dates_and_rules", "compliance_matrix", "technical_approach"
            ]
            
            missing_fields = [field for field in required_fields if field not in proposal_data]
            
            if missing_fields:
                print(f"[GEMINI] Warning: Missing required fields: {missing_fields}")
                proposal_data["_warnings"] = {
                    "missing_fields": missing_fields,
                    "message": "Some required sections are missing from the generated proposal"
                }
            
            # Add success metadata
            proposal_data["status"] = "success"
            proposal_data["message"] = "Proposal generated successfully"
            proposal_data["generated_at"] = datetime.now().isoformat()
            
            # Calculate word count
            total_words = 0
            for key, value in proposal_data.items():
                if isinstance(value, str):
                    total_words += len(value.split())
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            total_words += len(item.split())
            
            proposal_data["actual_word_count"] = total_words
            proposal_data["estimated_pages"] = f"{max(15, min(20, total_words // 600))}-{max(16, min(22, total_words // 500))}"
            
            print(f"[GEMINI] Proposal generated: {total_words} words, ~{proposal_data['estimated_pages']} pages")
            
            return proposal_data
            
        except Exception as e:
            print(f"[GEMINI] Exception: {type(e).__name__} - {str(e)}")
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "message": f"Error generating proposal: {str(e)}",
                "details": "Failed to process tender document. Please ensure the PDF is valid and readable.",
                "timestamp": datetime.now().isoformat()
            }