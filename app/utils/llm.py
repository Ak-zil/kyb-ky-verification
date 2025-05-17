import json
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("llm")


class BedrockClient:
    """Client for Amazon Bedrock LLM services"""

    def __init__(self):
        """Initialize Amazon Bedrock client"""
        config = Config(
            region_name=settings.AWS_REGION,
        )
        
        # Initialize bedrock client
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=config,
        )
        self.logger = logger
        
    async def invoke_model(
        self, 
        prompt: str, 
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Invoke Amazon Bedrock model to generate text
        
        Args:
            prompt: The prompt to send to the model
            model_id: The model ID to use
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            Dict containing the model response
        """
        try:
            if "anthropic" in model_id.lower():
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            elif "cohere" in model_id.lower():
                request_body = {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "p": top_p,
                }
            elif "deepseek" in model_id.lower():
                request_body = {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                }
            else:
                # Default to deepseek formatting
                request_body = {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                }
            
            response = self.client.invoke_model(
                body=json.dumps(request_body),
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            
            response_body = json.loads(response["body"].read())
            
            # Extract the generated text based on the model used
            if "anthropic" in model_id.lower():
                generation = response_body["content"][0]["text"]
            elif "cohere" in model_id.lower():
                generation = response_body["generations"][0]["text"]
            elif "deepseek" in model_id.lower():
                generation = response_body["generation"]
            else:
                generation = response_body.get("generation", "")
            
            return {"generation": generation, "raw_response": response_body}
        
        except Exception as e:
            self.logger.error(f"Error invoking LLM: {str(e)}")
            raise
    
    async def extract_structured_data(
        self, 
        data: Dict[str, Any], 
        extraction_instructions: str,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    ) -> Dict[str, Any]:
        """
        Extract structured data from unstructured input using LLM
        
        Args:
            data: The data to analyze
            extraction_instructions: Instructions for data extraction
            model_id: The model ID to use
            
        Returns:
            Dict containing the extracted structured data
        """
        try:
            prompt = f"""
            You are a data extraction expert. Extract the required information based on the following criteria:
            
            {extraction_instructions}
            
            Here is the data to analyze:
            {json.dumps(data, indent=2)}
            
            Respond ONLY with a valid JSON object containing the extraction results.
            """
            
            response = await self.invoke_model(
                prompt=prompt,
                model_id=model_id,
                max_tokens=2048,
                temperature=0.1
            )
            
            generation = response["generation"]
            
            # Try to parse the JSON response
            try:
                # Extract JSON content if embedded in markdown code blocks
                if "```json" in generation:
                    json_content = generation.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_content)
                else:
                    return json.loads(generation)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse LLM response as JSON: {generation}")
                # Fallback response
                return {
                    "error": "Failed to parse LLM response",
                    "raw_text": generation
                }
                
        except Exception as e:
            self.logger.error(f"Error extracting structured data: {str(e)}")
            raise


# Create singleton instance
bedrock_client = BedrockClient()