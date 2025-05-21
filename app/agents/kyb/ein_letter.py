from typing import Any, Dict
import re

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError

from app.utils.ocr import ocr_processor
from app.utils.s3_storage import s3_storage


class EinLetterAgent(BaseAgent):
    """Agent for verifying EIN (Employer Identification Number) letter in KYB workflow"""

    # Update in app/agents/kyb/ein_letter.py

    async def run(self) -> Dict[str, Any]:
        """
        Verify EIN letter
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            business_data = verification_data.get("business", {}).get("business_data", {})
            persona_data = verification_data.get("business", {}).get("persona_data", {})
            
            from app.integrations.external_database import external_db
            external_business_data = await external_db.get_business_data(
                business_data.get("business_id") or business_data.get("id")
            )
            
            # Extract business tax information
            business_name = business_data.get("business_name", "")
            tax_id = business_data.get("tax_id", "")
            
            # Get Persona inquiry ID
            persona_inquiry_id = business_data.get("persona_inquiry_id")
            
            # Process checks
            checks = []
            
            # Data structures to store document analysis results
            all_documents = []
            ein_letter_data = None
            
            # Download and analyze all documents if persona inquiry ID is available
            if persona_inquiry_id:
                # Get and store all documents from Persona
                document_info = await self.persona_client.get_and_store_documents(persona_inquiry_id)
                all_documents = document_info.get("documents", [])
                
                # Process all documents to find EIN letter data
                for document in all_documents:
                    if "s3_key" in document:
                        try:
                            # Download document from S3
                            document_bytes = await s3_storage.download_document(document["s3_key"])
                            
                            # Process document (classify and extract data)
                            document_result = await ocr_processor.process_document(document_bytes)
                            
                            # Store document processing result in the document
                            document["ocr_result"] = document_result
                            
                            # Check if this document appears to be an EIN letter
                            doc_type = document_result.get("classification", {}).get("document_type", "").lower()
                            doc_subtype = document_result.get("classification", {}).get("document_subtype", "").lower()
                            
                            # Look for keywords in classification
                            is_ein_letter = (
                                "ein" in doc_type or 
                                "tax" in doc_type or 
                                "irs" in doc_type or
                                "ein" in doc_subtype or 
                                "tax" in doc_subtype or 
                                "irs" in doc_subtype
                            )
                            
                            # If this appears to be an EIN letter, use it
                            if is_ein_letter and not ein_letter_data:
                                ein_letter_data = document_result.get("extracted_data", {})
                                self.logger.info(f"Found EIN letter data in document {document.get('name')}")
                            
                            # Even if not recognized as EIN letter, check the extracted data
                            # for EIN numbers that might suggest it's an EIN letter
                            extracted_data = document_result.get("extracted_data", {})
                            
                            # Check for EIN pattern in the extracted text
                            raw_text = document_result.get("raw_text", "")
                            ein_pattern = r'\b\d{2}-\d{7}\b'
                            has_ein_pattern = bool(re.search(ein_pattern, raw_text))
                            
                            # Check for key fields that would indicate an EIN letter
                            has_ein_fields = (
                                extracted_data.get("ein") or
                                (extracted_data.get("company_name") and has_ein_pattern) or
                                (extracted_data.get("is_official_irs_letter") is True)
                            )
                            
                            if has_ein_fields and not ein_letter_data:
                                ein_letter_data = extracted_data
                                self.logger.info(f"Found likely EIN letter data in document {document.get('name')}")
                            
                            # Even if we already found an EIN letter, check to see if this document is better
                            # (has more fields filled in)
                            if has_ein_fields and ein_letter_data:
                                current_field_count = sum(1 for v in ein_letter_data.values() if v)
                                new_field_count = sum(1 for v in extracted_data.values() if v)
                                
                                if new_field_count > current_field_count:
                                    self.logger.info(f"Found better EIN letter data in document {document.get('name')}")
                                    ein_letter_data = extracted_data
                            
                        except Exception as e:
                            self.logger.error(f"Error processing document {document.get('name')}: {str(e)}")
                            checks.append({
                                "name": f"Document Processing: {document.get('name')}",
                                "status": "failed",
                                "details": f"Error processing document: {str(e)}"
                            })
                            
                # Add checks for Persona document verifications
                for document in all_documents:
                    if "checks" in document:
                        doc_name = document.get("name", "Unknown Document")
                        for check in document.get("checks", []):
                            check_name = check.get("name")
                            check_status = check.get("status")
                            
                            # Convert Persona status to our status format
                            status = "passed" if check_status == "success" else "failed"
                            
                            checks.append({
                                "name": f"Persona: {doc_name} - {check_name}",
                                "status": status,
                                "details": f"Persona document check: {check_name} - {check_status}"
                            })
            
            # Add checks based on the found EIN letter data (if any)
            if ein_letter_data:
                # 1. Company Name Check
                ocr_company_name = ein_letter_data.get("company_name", "")
                name_match = False
                if ocr_company_name and business_name:
                    name_match = (
                        ocr_company_name.lower() in business_name.lower() or 
                        business_name.lower() in ocr_company_name.lower()
                    )
                
                checks.append({
                    "name": "Company Name Verification",
                    "status": "passed" if name_match else "failed",
                    "details": f"OCR company name: {ocr_company_name}, Business name: {business_name}, Match: {name_match}"
                })
                
                # 2. EIN Number Check
                ocr_ein = ein_letter_data.get("ein", "")
                ein_match = False
                if ocr_ein and tax_id:
                    # Normalize EIN formats for comparison (remove hyphens)
                    ocr_ein_normalized = ocr_ein.replace("-", "")
                    tax_id_normalized = tax_id.replace("-", "")
                    ein_match = ocr_ein_normalized == tax_id_normalized
                
                checks.append({
                    "name": "EIN Number Verification",
                    "status": "passed" if ein_match else "failed",
                    "details": f"OCR EIN: {ocr_ein}, Provided EIN: {tax_id}, Match: {ein_match}"
                })
                
                # 3. IRS Letter Authenticity Check
                is_official = ein_letter_data.get("is_official_irs_letter", False)
                letter_type = ein_letter_data.get("letter_type", "")
                
                authenticity_score = 0
                authenticity_details = []
                
                if is_official:
                    authenticity_score += 1
                    authenticity_details.append("Document appears to be an official IRS letter")
                
                if letter_type:
                    authenticity_score += 1
                    authenticity_details.append(f"Recognized as IRS letter type: {letter_type}")
                
                authenticity_status = "passed" if authenticity_score > 0 else "failed"
                
                checks.append({
                    "name": "IRS Letter Authenticity",
                    "status": authenticity_status,
                    "details": f"Authenticity assessment: {', '.join(authenticity_details)}"
                })
                
                # 4. EIN Letter Present Check
                checks.append({
                    "name": "EIN Letter Present",
                    "status": "passed",
                    "details": "EIN letter document found and processed"
                })
            else:
                # Add failed check if no EIN letter data found
                checks.append({
                    "name": "EIN Letter Present",
                    "status": "failed",
                    "details": "No EIN letter document found or could not be processed"
                })
            
            # Add standard verification checks (based on available data)
            
            # 1. EIN Letter Verification
            # In a real implementation, this would verify the EIN letter with OCR
            # For this example, use the mock external data
            ein_letter_verified = external_business_data.get("ein_letter_verified", False) or bool(ein_letter_data)
            
            checks.append({
                "name": "EIN Letter Verification",
                "status": "passed" if ein_letter_verified else "failed",
                "details": f"EIN letter verified: {ein_letter_verified}"
            })
            
            # 2. EIN Number Format Check
            # Verify EIN format is valid (9 digits, typically XX-XXXXXXX)
            ein_format_valid = tax_id and len(tax_id.replace("-", "")) == 9 and tax_id.replace("-", "").isdigit()
            
            checks.append({
                "name": "EIN Format Check",
                "status": "passed" if ein_format_valid else "failed",
                "details": f"EIN format valid: {ein_format_valid}, EIN: {tax_id}"
            })
            
            # 3. Business Name Match
            # Verify business name on EIN letter matches business name
            ein_owner_name = external_business_data.get("ein_owner_name", "")
            name_match = business_name.lower() == ein_owner_name.lower()
            
            checks.append({
                "name": "Business Name Match",
                "status": "passed" if name_match else "failed",
                "details": f"Business name match: {name_match}, Submitted: {business_name}, EIN letter: {ein_owner_name}"
            })
            
            # Use LLM to analyze the EIN letter verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data,
                    "ocr_data": ein_letter_data or {},
                    "all_documents": [
                        {
                            "name": doc.get("name", "Unknown Document"),
                            "ocr_result": doc.get("ocr_result", {}) if "ocr_result" in doc else {}
                        } 
                        for doc in all_documents
                    ]
                },
                prompt="""
                Analyze the EIN letter verification results and determine if there are any 
                concerns about its authenticity. Consider:
                1. EIN letter verification status
                2. EIN number format validity
                3. Business name consistency
                4. Letter authenticity indicators
                5. OCR data extracted from the document (if available)
                6. Persona document checks (if available)
                7. The full set of available documents
                
                Your response should include:
                1. An overall assessment of the EIN letter authenticity
                2. Any specific concerns or inconsistencies
                3. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "EinLetterAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "EIN letter verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"EIN letter verification error: {str(e)}")
            return {
                "agent_type": "EinLetterAgent",
                "status": "error",
                "details": f"Error during EIN letter verification: {str(e)}",
                "checks": []
            }
    