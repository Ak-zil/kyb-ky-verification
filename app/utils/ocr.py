import base64
from typing import Any, Dict, List, Optional
import json
import io
import os
import tempfile
import fitz  # PyMuPDF
import magic  # For MIME type detection

from app.utils.llm import BedrockClient
from app.utils.logging import get_logger

logger = get_logger("ocr")

class OCRProcessor:
    """OCR processor using Amazon Bedrock Claude for document text extraction and classification"""
    
    def __init__(self, bedrock_client: Optional[BedrockClient] = None):
        """Initialize OCR processor"""
        from app.utils.llm import bedrock_client as default_bedrock_client
        self.bedrock_client = bedrock_client or default_bedrock_client
        self.logger = logger
    
    async def process_document(self, document_bytes: bytes) -> Dict[str, Any]:
        """
        Process document with classification and extraction
        
        Args:
            document_bytes: Raw document bytes
            
        Returns:
            Dict containing document classification and extracted data
        """
        try:
            # Detect MIME type
            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(document_bytes)
            
            self.logger.info(f"Detected MIME type: {mime_type}")
            
            # Initialize variables
            images = []
            
            # Handle PDFs - convert to images
            if mime_type == 'application/pdf':
                self.logger.info("Converting PDF to images")
                
                # Create a temporary file to save the PDF
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                    temp_pdf.write(document_bytes)
                    pdf_path = temp_pdf.name
                
                try:
                    # Open PDF with PyMuPDF
                    pdf_document = fitz.open(pdf_path)
                    page_count = len(pdf_document)
                    
                    # Convert each page to an image
                    for page_num in range(min(page_count, 3)):  # Limit to first 3 pages
                        page = pdf_document.load_page(page_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Higher resolution
                        img_bytes = pix.tobytes("png")
                        images.append(img_bytes)
                    
                    pdf_document.close()
                    
                except Exception as pdf_error:
                    self.logger.error(f"Error converting PDF: {pdf_error}")
                    raise
                finally:
                    # Clean up the temporary file
                    if os.path.exists(pdf_path):
                        os.unlink(pdf_path)
                
                if not images:
                    self.logger.error("Failed to extract images from PDF")
                    raise ValueError("Could not extract images from PDF")
            else:
                # Handle image-based documents directly
                images = [document_bytes]
            
            # Process the first image for classification
            classification = await self.classify_document(images[0])
            document_type = classification.get("document_type", "generic")
            
            # Process the first image (or only image) for detailed extraction
            extraction_result = await self.extract_text_from_image(
                images[0], document_type=document_type
            )
            
            # Include additional information if we have multiple pages
            additional_info = {}
            if len(images) > 1:
                additional_info["is_multipage"] = True
                additional_info["page_count"] = len(images)
            
            return {
                "classification": classification,
                "extracted_data": extraction_result.get("extracted_data", {}),
                "raw_text": extraction_result.get("raw_text", ""),
                **additional_info
            }
            
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            raise
    
    async def classify_document(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Classify document type using Claude Vision
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dict containing document classification
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Construct prompt for document classification
            prompt = """
            Please analyze this document and determine what type of document it is. Focus especially on determining if this is one of these specific document types:
            
            1. Articles of Incorporation / Certificate of Organization / Business Formation Document
            2. EIN Letter / IRS Tax ID confirmation
            3. Government ID (driver's license, passport, etc.)
            4. Business License
            5. Bank Statement
            6. Utility Bill
            7. Secretary of State filing confirmation
            8. Proof of address document
            
            Please classify the document and extract key identifying information in JSON format:
            
            {
                "document_type": "The most specific document type from the list above, or 'other' if none match",
                "document_subtype": "More specific classification if applicable",
                "issuing_authority": "Organization that issued the document",
                "primary_entity": "The main business or person the document pertains to",
                "key_identifiers": ["List of any ID numbers, file numbers, or other key identifiers visible"],
                "dates": {
                    "issue_date": "YYYY-MM-DD if visible",
                    "expiration_date": "YYYY-MM-DD if visible"
                },
                "confidence": "high/medium/low - your confidence in this classification"
            }
            
            Provide the data in valid JSON format only.
            """
            
            # Create message with image
            model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Claude 3.7 Sonnet
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # Invoke Claude
            response = self.bedrock_client.client.invoke_model(
                body=json.dumps(request_body),
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            
            # Extract the generated text
            generation = response_body["content"][0]["text"]
            
            # Try to parse the JSON response if it contains JSON
            classification_data = {}
            try:
                if "```json" in generation:
                    json_content = generation.split("```json")[1].split("```")[0].strip()
                    classification_data = json.loads(json_content)
                elif generation.strip().startswith("{") and generation.strip().endswith("}"):
                    classification_data = json.loads(generation)
                else:
                    classification_data = {"document_type": "unknown", "raw_text": generation}
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse document classification response as JSON")
                classification_data = {"document_type": "unknown", "raw_text": generation}
            
            return classification_data
            
        except Exception as e:
            self.logger.error(f"Error classifying document: {str(e)}")
            raise
    
    async def extract_text_from_image(self, image_bytes: bytes, document_type: str = "generic") -> Dict[str, Any]:
        """
        Extract text from image using Claude Vision
        
        Args:
            image_bytes: Raw image bytes
            document_type: Type of document (e.g., "government_id", "articles_of_incorporation", "ein_letter")
            
        Returns:
            Dict containing extracted text and structured data
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Construct prompt based on document type
            prompt = self._construct_prompt_for_document_type(document_type)
            
            # Create message with image
            model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"  # Claude 3.7 Sonnet
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # Invoke Claude directly with image
            response = self.bedrock_client.client.invoke_model(
                body=json.dumps(request_body),
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            
            # Extract the generated text
            generation = response_body["content"][0]["text"]
            
            # Try to parse the JSON response if it contains JSON
            extracted_data = {}
            try:
                if "```json" in generation:
                    json_content = generation.split("```json")[1].split("```")[0].strip()
                    extracted_data = json.loads(json_content)
                elif generation.strip().startswith("{") and generation.strip().endswith("}"):
                    extracted_data = json.loads(generation)
                else:
                    extracted_data = {"full_text": generation}
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse OCR response as JSON")
                extracted_data = {"full_text": generation}
            
            return {
                "document_type": document_type,
                "extracted_data": extracted_data,
                "raw_text": generation
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {str(e)}")
            raise
            
    # The _construct_prompt_for_document_type method can remain unchanged
    
    # ... update existing _construct_prompt_for_document_type method to include more document types ...
    
    def _construct_prompt_for_document_type(self, document_type: str) -> str:
        """
        Construct OCR prompt based on document type
        
        Args:
            document_type: Type of document
            
        Returns:
            Formatted prompt
        """
        if document_type == "articles_of_incorporation" or document_type == "certificate_of_organization":
            return """
            Please analyze this business formation document (Articles of Incorporation or Certificate of Organization) and extract the following information in JSON format:
            
            {
                "company_name": "Full legal name of the company",
                "type_of_entity": "LLC, Corporation, etc.",
                "state_of_incorporation": "State where incorporated",
                "date_of_incorporation": "Date in YYYY-MM-DD format",
                "registered_agent": "Name of the registered agent",
                "registered_office_address": "Address of the registered office",
                "business_purpose": "Stated purpose of the business",
                "authorized_shares": "Number of authorized shares (if applicable)",
                "incorporators": ["List of incorporator names"],
                "directors": ["List of director names if present"],
                "filing_number": "Document filing number if present",
                "effective_date": "Effective date of the document if different from incorporation date"
            }
            
            Provide the data in valid JSON format only. If any field is not found in the document, leave it as an empty string.
            """
            
        elif document_type == "ein_letter":
            return """
            Please analyze this EIN (Employer Identification Number) letter or tax ID confirmation and extract the following information in JSON format:
            
            {
                "company_name": "Business name as it appears on the letter",
                "ein": "The EIN number (XX-XXXXXXX format)",
                "address": "Business address",
                "issue_date": "Date the EIN was issued (YYYY-MM-DD format)",
                "tax_classification": "Tax classification if mentioned (e.g., S-Corp, LLC, etc.)",
                "is_official_irs_letter": true/false,
                "letter_type": "SS-4, CP-575, 147C, etc.",
                "responsible_party": "Name of the responsible party if mentioned"
            }
            
            Provide the data in valid JSON format only. If any field is not found in the document, leave it as an empty string.
            """
            
        elif document_type == "business_license":
            return """
            Please analyze this business license document and extract the following information in JSON format:
            
            {
                "business_name": "Full legal name of the business",
                "license_number": "The business license number",
                "license_type": "Type of license",
                "issuing_authority": "Authority that issued the license",
                "issue_date": "Date issued in YYYY-MM-DD format",
                "expiration_date": "Expiration date in YYYY-MM-DD format",
                "business_address": "Physical address of the business",
                "business_owner": "Name of the business owner if listed",
                "business_activity": "Licensed business activity or classification"
            }
            
            Provide the data in valid JSON format only. If any field is not found in the document, leave it as an empty string.
            """
            
        elif document_type == "secretary_of_state_filing":
            return """
            Please analyze this Secretary of State filing document and extract the following information in JSON format:
            
            {
                "business_name": "Full legal name of the business",
                "filing_number": "The filing or document number",
                "filing_type": "Type of filing (annual report, etc.)",
                "filing_date": "Date of filing in YYYY-MM-DD format",
                "effective_date": "Effective date in YYYY-MM-DD format if different",
                "status": "Business status (active, dissolved, etc.)",
                "jurisdiction": "State or jurisdiction of filing",
                "registered_agent": "Name of registered agent if present",
                "business_address": "Business address if listed"
            }
            
            Provide the data in valid JSON format only. If any field is not found in the document, leave it as an empty string.
            """
            
        else:  # generic document
            return """
            Please analyze this document and extract all relevant business verification information. Look for:
            
            1. Any business name, EIN/Tax ID numbers, or business identifiers
            2. Business formation information (type, date, state)
            3. Business address or contact information
            4. Any official filing numbers or reference numbers
            5. Any dates (issue dates, effective dates, expiration dates)
            6. Names of owners, officers, directors, or registered agents
            7. Any compliance or status information
            
            Provide the data in JSON format:
            
            {
                "document_type": "Your assessment of what type of document this is",
                "business_name": "Name of the business if present",
                "business_identifiers": {
                    "ein": "Tax ID if present",
                    "filing_number": "Any filing or registration numbers",
                    "other_ids": ["Any other identifying numbers found"]
                },
                "business_details": {
                    "type": "Business entity type if present",
                    "formation_date": "Date in YYYY-MM-DD format if present",
                    "jurisdiction": "State or jurisdiction if present"
                },
                "addresses": ["All business addresses found"],
                "key_individuals": ["Names of owners/officers/agents found"],
                "key_dates": {
                    "issue_date": "YYYY-MM-DD if present",
                    "effective_date": "YYYY-MM-DD if present", 
                    "expiration_date": "YYYY-MM-DD if present"
                },
                "status": "Any status information found"
            }
            
            Provide the data in valid JSON format only. If any field is not found in the document, leave it as an empty string or empty array.
            """
        

ocr_processor = OCRProcessor()