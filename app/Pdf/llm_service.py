from google import genai
from google.genai.types import Part
import json
import re
from typing import Dict, Any, List
import os
from datetime import datetime
from app.config import settings

class GeminiPDFService:
    def __init__(self, api_key: str):
        """Initialize Gemini client with API key"""
        self.client = genai.Client(api_key=api_key)
        self.model_id = settings.GEMINI_MODEL
        
    def _clean_json_string(self, text: str) -> str:
        """
        Clean and prepare text for JSON parsing
        Handles control characters, markdown blocks, and malformed JSON
        """
        # Remove markdown code block wrappers - aggressive stripping
        text = text.strip()
        
        # Remove all variations of markdown code blocks - MORE AGGRESSIVE
        # Handle ```json, ```, etc. - strip from both ends MULTIPLE TIMES
        for _ in range(10):  # Increased from 5 to 10 passes
            original_text = text
            
            # Remove from start
            if text.startswith("```json\n"):
                text = text[8:].strip()
            elif text.startswith("```json"):
                text = text[7:].strip()
            elif text.startswith("```\n"):
                text = text[4:].strip()
            elif text.startswith("```"):
                text = text[3:].strip()
            
            # Remove from end
            if text.endswith("\n```"):
                text = text[:-4].strip()
            elif text.endswith("```"):
                text = text[:-3].strip()
            
            # If nothing changed, we're done
            if text == original_text:
                break
        
        # Extract JSON object (find first { and last })
        # This handles cases where the API adds text before/after JSON
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
        # Strategy 1: Direct parse (fastest path)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[JSON PARSE] Strategy 1 (direct) failed at position {e.pos}: {e.msg}")
        
        # Strategy 2: Clean markdown/control chars and parse
        try:
            cleaned = self._clean_json_string(text)
            print(f"[JSON PARSE] Strategy 2: After cleaning, length={len(cleaned)}, starts with: {cleaned[:50]}")
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[JSON PARSE] Strategy 2 (cleaned) failed at position {e.pos}: {e.msg}")
            print(f"[JSON PARSE] Context around error: ...{cleaned[max(0, e.pos-50):min(len(cleaned), e.pos+50)]}...")
        
        # Strategy 3: Try to fix unescaped newlines - more careful approach
        try:
            cleaned = self._clean_json_string(text)
            
            # Find all string boundaries and escape newlines within them
            # This regex finds quoted strings and their content
            def escape_newlines_in_strings(s):
                result = []
                i = 0
                while i < len(s):
                    if s[i] == '"':
                        # Found start of string - collect until end
                        result.append('"')
                        i += 1
                        while i < len(s):
                            if s[i] == '\\':
                                # Escape sequence - keep as-is
                                result.append(s[i])
                                if i + 1 < len(s):
                                    result.append(s[i + 1])
                                    i += 2
                                else:
                                    i += 1
                            elif s[i] == '"':
                                # End of string
                                result.append('"')
                                i += 1
                                break
                            elif s[i] == '\n':
                                # Unescaped newline - escape it
                                result.append('\\n')
                                i += 1
                            elif s[i] == '\r':
                                # Unescaped carriage return
                                result.append('\\r')
                                i += 1
                            elif s[i] == '\t':
                                # Unescaped tab
                                result.append('\\t')
                                i += 1
                            else:
                                result.append(s[i])
                                i += 1
                    else:
                        result.append(s[i])
                        i += 1
                
                return ''.join(result)
            
            fixed = escape_newlines_in_strings(cleaned)
            print(f"[JSON PARSE] Strategy 3: After escaping newlines, attempting parse...")
            return json.loads(fixed)
        except Exception as e:
            print(f"[JSON PARSE] Strategy 3 (escape newlines) failed: {type(e).__name__}: {e}")
        
        # Strategy 4: Try to close incomplete JSON (truncated response)
        try:
            cleaned = self._clean_json_string(text)
            
            # Count unclosed braces and brackets
            open_braces = 0
            open_brackets = 0
            in_string = False
            escape_next = False
            
            for char in cleaned:
                if escape_next:
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    continue
                
                if char == '"' and not escape_next:
                    in_string = not in_string
                
                if not in_string:
                    if char == '{':
                        open_braces += 1
                    elif char == '}':
                        open_braces -= 1
                    elif char == '[':
                        open_brackets += 1
                    elif char == ']':
                        open_brackets -= 1
            
            if open_braces > 0 or open_brackets > 0:
                print(f"[JSON PARSE] Strategy 4: JSON incomplete - {open_braces} unclosed braces, {open_brackets} unclosed brackets. Closing...")
                fixed = cleaned + ('}' * open_braces) + (']' * open_brackets)
                result = json.loads(fixed)
                print(f"[JSON PARSE] Strategy 4: Successfully parsed truncated JSON")
                return result
        except Exception as e:
            print(f"[JSON PARSE] Strategy 4 (truncation fix) failed: {type(e).__name__}: {e}")
        
        # Strategy 5: Extract and merge multiple JSON objects
        try:
            cleaned = self._clean_json_string(text)
            json_objects = []
            depth = 0
            current_obj = ""
            in_string = False
            escape_next = False
            
            for char in cleaned:
                if escape_next:
                    current_obj += char
                    escape_next = False
                    continue
                
                if char == '\\':
                    current_obj += char
                    escape_next = True
                    continue
                
                if char == '"':
                    current_obj += char
                    in_string = not in_string
                    continue
                
                if not in_string:
                    if char == '{':
                        depth += 1
                        current_obj += char
                    elif char == '}':
                        current_obj += char
                        depth -= 1
                        if depth == 0 and current_obj.strip():
                            try:
                                obj = json.loads(current_obj)
                                json_objects.append(obj)
                                current_obj = ""
                            except:
                                pass
                    else:
                        current_obj += char
                else:
                    current_obj += char
            
            if len(json_objects) > 0:
                print(f"[JSON PARSE] Strategy 5: Found {len(json_objects)} JSON objects, merging...")
                merged = {}
                for obj in json_objects:
                    if isinstance(obj, dict):
                        merged.update(obj)
                if merged:
                    return merged
        except Exception as e:
            print(f"[JSON PARSE] Strategy 5 (multiple objects merge) failed: {type(e).__name__}: {e}")
        
        # All strategies failed
        raise ValueError("All JSON parsing strategies failed")
        
    def generate_proposal(
        self, 
        tender_pdf_bytes: bytes,
        supporting_docs: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze government tender PDF and generate a comprehensive proposal
        with optional supporting documents
        
        Args:
            tender_pdf_bytes: Main tender PDF file content in bytes (REQUIRED)
            supporting_docs: Optional list of supporting documents with structure:
                [
                    {
                        "bytes": bytes,
                        "category": str,  # e.g., "Capability Statement", "Certificate", etc.
                        "filename": str
                    }
                ]
            
        Returns:
            Dict containing the generated proposal in JSON format
        """
        
        # Build enhanced prompt based on supporting documents
        supporting_context = ""
        if supporting_docs and len(supporting_docs) > 0:
            supporting_context = "\n\n**SUPPORTING DOCUMENTS PROVIDED:**\n"
            supporting_context += "The following supporting documents have been provided to enhance the proposal:\n"
            
            for idx, doc in enumerate(supporting_docs, 1):
                category = doc.get('category', 'Supporting Document')
                filename = doc.get('filename', f'Document {idx}')
                supporting_context += f"{idx}. **{category}**: {filename}\n"
            
            supporting_context += """
**Instructions for using supporting documents:**
- **Capability Statements**: Extract company strengths, past performance, and qualifications to enhance the Organizational Capability section
- **Certificates**: Reference relevant certifications in the Compliance Matrix and Organizational Capability sections
- **Past Proposals**: Learn from successful approaches and adapt methodologies for the Technical Approach section
- **Company Profiles**: Use company information to strengthen the Title Page, Executive Summary, and Organizational Capability
- **Success Stories**: Incorporate case studies and achievements into the Organizational Capability and Recommendations sections
- **Others/Supporting Docs**: Integrate relevant information throughout the proposal as appropriate

**CRITICAL**: The FIRST PDF is the MAIN TENDER DOCUMENT. All subsequent PDFs are supporting materials to enhance the proposal quality. Always prioritize information from the main tender document when making decisions about requirements, deadlines, and specifications.
"""
        
        prompt = f"""
You are an expert government tender analyst and proposal writer. 
Analyze the provided government tender document and create a comprehensive, professional proposal response.

**PRIMARY DOCUMENT**: The FIRST PDF is the main government tender/RFP document that contains all requirements, specifications, and evaluation criteria.
{supporting_context}

**CRITICAL OUTPUT REQUIREMENT**: You MUST respond with ONLY a valid JSON object. DO NOT wrap the JSON in markdown code blocks (```json or ```). DO NOT add any text before or after the JSON object. Return ONLY the raw JSON.

Your response should follow this structure:
{{
    "document_overview": "A comprehensive 1000-1200 word overview that summarizes the entire tender document. This should give readers a complete understanding of: the tendering organization, project scope, objectives, budget range, evaluation criteria, and overall requirements. Make this section detailed and informative.",
    
    "title_page": {{
        "tender_title": "Extract the exact tender/project title",
        "tender_reference_number": "Tender/RFP reference number",
        "issuing_authority": "Government department/organization issuing the tender",
        "proposal_submitted_by": "Your organization name (use company name from Company Profile if provided, otherwise use placeholder like 'Bidding Organization')",
        "submission_date": "Today's date or deadline date"
    }},
    
    "executive_summary": "Write a compelling 800-1000 word executive summary that: highlights your understanding of the tender requirements, outlines your proposed solution approach, emphasizes your key strengths and differentiators (reference capability statements and success stories if provided), summarizes expected outcomes and benefits. Make this persuasive and professional.",
    
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
    
    "compliance_matrix": "Write a detailed 700-900 word section that: maps each tender requirement to your proposed solution, demonstrates how you meet technical specifications (reference certificates and qualifications if provided), shows compliance with eligibility criteria, addresses evaluation parameters, highlights certifications and qualifications. Use descriptive paragraphs, not bullet points.",
    
    "technical_approach": "Provide a comprehensive 1200-1400 word description of: your proposed methodology (learn from past proposals if provided), implementation strategy, technical architecture (if applicable), resource allocation plan, quality assurance measures, risk management approach, timeline and milestones. Be detailed and specific. If past proposals are provided, adapt successful approaches while maintaining originality.",
    
    "risks_and_gaps": [
        "• Risk: [Identified risk from tender analysis]",
        "• Gap: [Any missing information or unclear requirement]",
        "• Challenge: [Potential implementation challenge]",
        "• Mitigation: [Your proposed mitigation strategy]",
        "• Assumption: [Any assumptions made due to unclear requirements]"
    ],
    
    "financial_proposal_overview": "Write a 600-700 word overview covering: cost structure approach, pricing methodology, value for money justification, payment terms understanding, budget optimization strategies. Do NOT include actual prices (those come in separate financial bid).",
    
    "organizational_capability": "Provide 700-800 words describing: your organization's experience with similar projects (use capability statements and success stories if provided), relevant case studies, team qualifications (reference certificates), infrastructure and resources, certifications and accreditations, past performance with government projects. If company profile is provided, integrate that information here.",
    
    "recommendations_and_value_additions": "Write 700-800 words detailing: innovative solutions beyond basic requirements, value-added services (reference success stories if provided), sustainability considerations, long-term benefits, post-implementation support, continuous improvement suggestions.",
    
    "implementation_timeline": "Provide a detailed 500-600 word description of: project phases, key milestones, deliverable schedule, resource deployment plan, quality checkpoints, testing and acceptance procedures.",
    
    "appendix": {{
        "required_documents_checklist": ["List of all documents mentioned in tender that need to be attached"],
        "compliance_certificates": ["Certifications required - reference any certificates provided in supporting documents"],
        "technical_specifications_summary": "Brief summary of key technical specs",
        "references": ["Any standards, regulations, or documents referenced"],
        "abbreviations_and_glossary": {{"Term": "Definition of technical terms used"}},
        "supporting_documents_used": ["List the supporting documents that were referenced in creating this proposal"]
    }},
    
    "metadata": {{
        "proposal_pages": "15-20",
        "word_count": "Approximately 10,000-12,000 words",
        "analysis_date": "Current date",
        "tender_type": "Identified tender category (e.g., IT Services, Construction, Consulting)",
        "estimated_value": "Tender value if mentioned",
        "supporting_docs_count": "{len(supporting_docs) if supporting_docs else 0}",
        "enhanced_by": ["List categories of supporting documents used"]
    }}
}}

CRITICAL INSTRUCTIONS:
1. **Primary Focus**: The FIRST PDF contains the tender requirements. This is your primary source.

2. **Supporting Documents Integration**: Use supporting documents to ENHANCE the proposal quality:
   - Capability Statements → Strengthen organizational capability section
   - Certificates → Reference in compliance matrix and qualifications
   - Past Proposals → Learn methodologies but create original content
   - Company Profiles → Use for title page and company information
   - Success Stories → Include in organizational capability as case studies
   - Others → Integrate relevant information appropriately

3. **Dynamic Headlines**: Create section headings based on the actual tender content.

4. **Key Dates and Rules**: Present as bullet points (•) with clear, concise information.

5. **Risks and Gaps**: Present as bullet points (•) highlighting specific concerns and mitigation strategies.

6. **All Other Sections**: Write in detailed, descriptive paragraphs. Be comprehensive and professional.

7. **Document Overview**: Make it detailed enough that someone reading only this section understands the complete tender.

8. **Word Count**: Aim for 10,000-12,000 total words to ensure 15-20 pages of content.

9. **Professional Tone**: Use formal business language appropriate for government proposals.

10. **Specificity**: Base everything on the actual tender document. Extract real dates, numbers, requirements.

11. **Valid JSON**: Ensure your response is properly formatted JSON that can be parsed. DO NOT use markdown code blocks.

12. **Completeness**: Fill all sections with meaningful content. Never use placeholders like "TBD" or "Not specified".

13. **Attribution**: In the appendix, list which supporting documents were actually used to enhance the proposal.

**REMINDER**: Output ONLY the JSON object. No markdown, no code blocks, no explanatory text. Just the pure JSON starting with {{ and ending with }}.

Now analyze the provided tender document and supporting materials to generate a complete, professional proposal.
"""

        try:
            # Create list to hold all file parts
            file_parts = []
            
            # Add main tender PDF (REQUIRED - always first)
            tender_pdf = Part.from_bytes(
                data=tender_pdf_bytes,
                mime_type="application/pdf",
            )
            file_parts.append(tender_pdf)
            
            # Add supporting documents if provided
            if supporting_docs:
                print(f"[GEMINI] Adding {len(supporting_docs)} supporting documents...")
                for doc in supporting_docs:
                    doc_part = Part.from_bytes(
                        data=doc['bytes'],
                        mime_type="application/pdf",
                    )
                    file_parts.append(doc_part)
            
            # Generate content using Gemini
            print(f"[GEMINI] Sending request to {self.model_id}...")
            print(f"[GEMINI] Total documents: {len(file_parts)} (1 tender + {len(supporting_docs) if supporting_docs else 0} supporting)")
            
            # Combine files with prompt
            contents = file_parts + [prompt]
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
            )
            
            print(f"[GEMINI] Response received, parsing JSON...")
            
            # Get response text
            report_text = response.text.strip()
            
            # Log first and last 200 chars for debugging
            print(f"[GEMINI] Response length: {len(report_text)} chars")
            print(f"[GEMINI] Response starts: {report_text[:200]}...")
            print(f"[GEMINI] Response ends: ...{report_text[-200:]}")
            
            # Parse JSON with multiple strategies
            try:
                proposal_data = self._parse_json_safely(report_text)
                print(f"[JSON PARSE] ✓ Successfully parsed JSON")
            except ValueError as ve:
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
            
            # Add supporting docs info
            if supporting_docs:
                proposal_data["supporting_documents_info"] = {
                    "count": len(supporting_docs),
                    "categories": [doc.get('category', 'Unknown') for doc in supporting_docs],
                    "filenames": [doc.get('filename', 'Unknown') for doc in supporting_docs]
                }
            
            print(f"[GEMINI] Proposal generated successfully")
            print(f"[GEMINI] Word count: {total_words}, Estimated pages: {proposal_data['estimated_pages']}")
            if supporting_docs:
                print(f"[GEMINI] Enhanced with {len(supporting_docs)} supporting documents")
            
            return proposal_data
            
        except Exception as e:
            print(f"[GEMINI] Exception: {type(e).__name__} - {str(e)}")
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "message": f"Error generating proposal: {str(e)}",
                "details": "Failed to process tender document. Please ensure all PDFs are valid and readable.",
                "timestamp": datetime.now().isoformat()
            }