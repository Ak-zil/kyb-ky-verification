from typing import Any, Dict, List, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError
from app.utils.ocr import ocr_processor
from app.utils.s3_storage import s3_storage


class ArticlesIncorporationAgent(BaseAgent):
    """Agent for verifying articles of incorporation in KYB workflow"""

    # Update in app/agents/kyb/articles_incorporation.py

    async def run(self) -> Dict[str, Any]:
        """
        Verify articles of incorporation
        
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
            
            # Extract business legal information
            business_name = business_data.get("business_name", "")
            business_type = business_data.get("business_type", "")
            incorporation_date = external_business_data.get("incorporation_date", "")
            legal_structure = external_business_data.get("legal_structure", "")
            
            # Get Persona inquiry ID
            persona_inquiry_id = business_data.get("persona_inquiry_id")
            
            # Process checks
            checks = []
            
            # Data structures to store document analysis results
            all_documents = []
            articles_data = None
            
            # Download and analyze all documents if persona inquiry ID is available
            if persona_inquiry_id:
                # Get and store all documents from Persona
                document_info = await self.persona_client.get_and_store_documents(persona_inquiry_id)
                all_documents = document_info.get("documents", [])


                
                # Process all documents to find articles of incorporation data
                for document in all_documents:
                    if "s3_key" in document:
                        try:
                            # Download document from S3
                            document_bytes = await s3_storage.download_document(document["s3_key"])
                            
                            # Process document (classify and extract data)
                            document_result = await ocr_processor.process_document(document_bytes)
                            
                            # Store document processing result in the document
                            document["ocr_result"] = document_result
                            
                            # Check if this document appears to be articles of incorporation
                            doc_type = document_result.get("classification", {}).get("document_type", "").lower()
                            doc_subtype = document_result.get("classification", {}).get("document_subtype", "").lower()
                            
                            # Look for keywords in classification
                            is_articles = (
                                "article" in doc_type or 
                                "incorporation" in doc_type or 
                                "certificate" in doc_type or
                                "organization" in doc_type or
                                "formation" in doc_type or
                                "article" in doc_subtype or 
                                "incorporation" in doc_subtype or 
                                "certificate" in doc_subtype or
                                "organization" in doc_subtype or
                                "formation" in doc_subtype
                            )
                            
                            # If this appears to be articles of incorporation, use it
                            if is_articles and not articles_data:
                                articles_data = document_result.get("extracted_data", {})
                                self.logger.info(f"Found articles of incorporation data in document {document.get('name')}")
                            
                            # Even if not recognized as articles, check the extracted data
                            # for identifying information that might suggest it's an articles document
                            extracted_data = document_result.get("extracted_data", {})
                            
                            # Check for key fields that would indicate articles of incorporation
                            has_incorporation_fields = (
                                extracted_data.get("company_name") and
                                (extracted_data.get("type_of_entity") or 
                                extracted_data.get("state_of_incorporation") or
                                extracted_data.get("date_of_incorporation"))
                            )
                            
                            if has_incorporation_fields and not articles_data:
                                articles_data = extracted_data
                                self.logger.info(f"Found likely articles of incorporation data in document {document.get('name')}")
                            
                            # Even if we already found articles, check to see if this document is better
                            # (has more fields filled in)
                            if has_incorporation_fields and articles_data:
                                current_field_count = sum(1 for v in articles_data.values() if v)
                                new_field_count = sum(1 for v in extracted_data.values() if v)
                                
                                if new_field_count > current_field_count:
                                    self.logger.info(f"Found better articles of incorporation data in document {document.get('name')}")
                                    articles_data = extracted_data
                            
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
            
            # Add checks based on the found articles data (if any)
            if articles_data:
                # 1. Company Name Check
                ocr_company_name = articles_data.get("company_name", "")
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
                
                # 2. Entity Type Check
                ocr_entity_type = articles_data.get("type_of_entity", "")
                entity_match = False
                if ocr_entity_type:
                    entity_match = (
                        (business_type.lower() in ocr_entity_type.lower()) or
                        (legal_structure.lower() in ocr_entity_type.lower()) or
                        ("llc" in ocr_entity_type.lower() and "llc" in business_type.lower()) or
                        ("corporation" in ocr_entity_type.lower() and "corporation" in business_type.lower()) or
                        ("corp" in ocr_entity_type.lower() and "corporation" in business_type.lower()) or
                        ("inc" in ocr_entity_type.lower() and "corporation" in business_type.lower())
                    )
                
                checks.append({
                    "name": "Entity Type Verification",
                    "status": "passed" if entity_match else "failed",
                    "details": f"OCR entity type: {ocr_entity_type}, Business type: {business_type}, Legal structure: {legal_structure}, Match: {entity_match}"
                })
                
                # 3. Incorporation Date Check
                ocr_date = articles_data.get("date_of_incorporation", "")
                date_match = False
                if ocr_date and incorporation_date:
                    # Normalize date formats for comparison
                    try:
                        ocr_date_obj = datetime.fromisoformat(ocr_date.replace('/', '-').replace('.', '-'))
                        incorporation_date_obj = datetime.fromisoformat(incorporation_date)
                        date_match = ocr_date_obj.date() == incorporation_date_obj.date()
                    except (ValueError, TypeError):
                        date_match = False
                
                checks.append({
                    "name": "Incorporation Date Verification",
                    "status": "passed" if date_match else "failed",
                    "details": f"OCR incorporation date: {ocr_date}, Recorded date: {incorporation_date}, Match: {date_match}"
                })
                
                # 4. State/Jurisdiction Check
                ocr_state = articles_data.get("state_of_incorporation", "")
                state_match = False
                if ocr_state and business_data.get("address", {}).get("state"):
                    state_match = ocr_state.lower() == business_data.get("address", {}).get("state").lower()
                
                checks.append({
                    "name": "Jurisdiction Verification",
                    "status": "passed" if state_match else "failed",
                    "details": f"OCR state: {ocr_state}, Business state: {business_data.get('address', {}).get('state')}, Match: {state_match}"
                })
                
                # 5. Documents Present Check
                checks.append({
                    "name": "Articles Document Present",
                    "status": "passed",
                    "details": "Articles of incorporation document found and processed"
                })
            else:
                # Add failed check if no articles data found
                checks.append({
                    "name": "Articles Document Present",
                    "status": "failed",
                    "details": "No articles of incorporation document found or could not be processed"
                })
            
            # Add standard verification checks (based on available data)
            # These checks are performed using external database data as a fallback
            
            # 1. Articles of Incorporation Verification
            articles_verified = bool(incorporation_date) or bool(articles_data)
            
            checks.append({
                "name": "Articles Verification",
                "status": "passed" if articles_verified else "failed",
                "details": f"Articles of incorporation verified: {articles_verified}"
            })
            
            # 2. Legal Structure Check
            legal_structure_valid = legal_structure in ["LLC", "Corporation", "Partnership", "Sole Proprietorship"]
            legal_structure_consistency = (
                (business_type.lower() == "llc" and legal_structure == "LLC") or
                (business_type.lower() == "corporation" and legal_structure == "Corporation") or
                (business_type.lower() == "partnership" and legal_structure == "Partnership") or
                (business_type.lower() == "sole_proprietorship" and legal_structure == "Sole Proprietorship")
            )
            
            checks.append({
                "name": "Legal Structure",
                "status": "passed" if legal_structure_valid and legal_structure_consistency else "failed",
                "details": f"Legal structure: {legal_structure}, Business type: {business_type}, Consistent: {legal_structure_consistency}"
            })
            
            # 3. Incorporation Date Check
            if incorporation_date:
                incorporation_datetime = datetime.fromisoformat(incorporation_date)
                business_age = (datetime.utcnow() - incorporation_datetime).days
                
                # Flag very new businesses (less than 30 days old)
                very_new_business = business_age < 30
                
                checks.append({
                    "name": "Incorporation Date",
                    "status": "warning" if very_new_business else "passed",
                    "details": f"Incorporation date: {incorporation_date}, Business age: {business_age} days"
                })
            else:
                checks.append({
                    "name": "Incorporation Date",
                    "status": "failed",
                    "details": "Incorporation date not available"
                })
            
            # Use LLM to analyze the articles of incorporation verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "business_data": business_data,
                    "external_business_data": external_business_data,
                    "ocr_data": articles_data or {},
                    "all_documents": [
                        {
                            "name": doc.get("name", "Unknown Document"),
                            "ocr_result": doc.get("ocr_result", {}) if "ocr_result" in doc else {}
                        } 
                        for doc in all_documents
                    ]
                },
                prompt="""
                Analyze the articles of incorporation verification results and determine 
                if there are any concerns about business legitimacy. Consider:
                1. Articles of incorporation verification status
                2. Legal structure consistency
                3. Incorporation date and business age
                4. Business name consistency
                5. OCR data extracted from the document (if available)
                6. Persona document checks (if available)
                7. The full set of available documents
                
                Your response should include:
                1. An overall assessment of business legitimacy based on incorporation documents
                2. Any specific concerns or red flags
                3. Recommendations for additional verification if needed
                """
            )
            
            return {
                "agent_type": "ArticlesIncorporationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Articles of incorporation verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Articles of incorporation verification error: {str(e)}")
            return {
                "agent_type": "ArticlesIncorporationAgent",
                "status": "error",
                "details": f"Error during articles of incorporation verification: {str(e)}",
                "checks": []
            }