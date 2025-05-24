import json
from typing import Any, Dict
from contextlib import asynccontextmanager

import aioboto3
from botocore.config import Config

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger("llm")


class BedrockClient:
    """Async client for Amazon Bedrock LLM services"""

    def __init__(self):
        """Initialize Amazon Bedrock client"""
        self.config = Config(
            region_name=settings.AWS_REGION,
            # Add retry configuration for better reliability
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            }
        )
        
        # Session will be created when needed
        self._session = None
        self.logger = logger
        
    async def _get_session(self):
        """Get or create aioboto3 session"""
        if self._session is None:
            self._session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        return self._session
        
    @asynccontextmanager
    async def _get_client(self):
        """Context manager for getting bedrock client"""
        session = await self._get_session()
        async with session.client(
            service_name="bedrock-runtime",
            region_name=settings.AWS_REGION,
            config=self.config,
        ) as client:
            yield client
        
    async def invoke_model(
        self, 
        prompt: str, 
        model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Async invoke Amazon Bedrock model to generate text
        
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
            # Prepare request body based on model type
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

            # Use async context manager for client
            async with self._get_client() as client:
                response = await client.invoke_model(
                    body=json.dumps(request_body),
                    modelId=model_id,
                    accept="application/json",
                    contentType="application/json"
                )
                
                # Read response body
                response_body_bytes = await response["body"].read()
                response_body = json.loads(response_body_bytes)
                
                # Extract the generated text based on the model used
                if "anthropic" in model_id.lower():
                    generation = response_body["content"][0]["text"]
                elif "cohere" in model_id.lower():
                    generation = response_body["generations"][0]["text"]
                elif "deepseek" in model_id.lower():
                    generation = response_body.get("generation", "")
                else:
                    # Try to extract from common response formats
                    generation = (
                        response_body.get("generation", "") or
                        response_body.get("text", "") or
                        str(response_body)
                    )
                
                self.logger.info(f"Successfully invoked model {model_id}")
                
                return {
                    "generation": generation,
                    "response_body": response_body
                }
                
        except Exception as e:
            self.logger.error(f"Error invoking Bedrock model {model_id}: {str(e)}")
            raise

    async def extract_structured_data(
        self,
        data: Dict[str, Any],
        extraction_instructions: str,
        model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    ) -> Dict[str, Any]:
        """
        Extract structured data using LLM
        
        Args:
            data: Input data to analyze
            extraction_instructions: Instructions for extraction
            model_id: Model ID to use
            
        Returns:
            Dict containing extracted structured data
        """
        try:
            # Format the prompt
            prompt = f"""
            You are a data analysis expert. Please analyze the following data and extract the requested information.
            
            Extraction Instructions:
            {extraction_instructions}
            
            Data to analyze:
            {json.dumps(data, indent=2)}
            
            Please respond with a valid JSON object containing the extracted information. 
            Do not include any text outside of the JSON response.
            """
            
            # Invoke the model
            response = await self.invoke_model(
                prompt=prompt,
                model_id=model_id,
                temperature=0.1  # Low temperature for structured extraction
            )
            
            generation = response.get("generation", "")
            
            # Try to parse the JSON response
            try:
                # Clean the response to extract JSON
                json_start = generation.find('{')
                json_end = generation.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = generation[json_start:json_end]
                    extracted_data = json.loads(json_str)
                    return extracted_data
                else:
                    # If no JSON found, return the raw response in a structured format
                    return {"raw_response": generation}
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON from LLM response: {str(e)}")
                return {"raw_response": generation, "parse_error": str(e)}
                
        except Exception as e:
            self.logger.error(f"Error in structured data extraction: {str(e)}")
            raise

    async def close(self):
        """Close the client session"""
        if self._session:
            # aioboto3 sessions are automatically cleaned up
            self._session = None
            self.logger.info("Bedrock client session closed")


# Create singleton instance
bedrock_client = BedrockClient()