import json
from typing import Any, Dict, Optional

from app.core.exceptions import AgentExecutionError
from app.integrations.database import Database
from app.integrations.persona import PersonaClient
from app.integrations.sift import SiftClient
from app.utils.json_encoder import convert_dates_to_strings
from app.utils.connection_pool import connection_pool
from app.utils.logging import get_logger


class BaseAgent:
    """Base class for all verification agents"""

    def __init__(
        self,
        verification_id: str,
        bedrock_client: Optional[str] = None,  # This is now unused but kept for compatibility
        db_client: Optional[Database] = None,
        persona_client: Optional[PersonaClient] = None,
        sift_client: Optional[SiftClient] = None,
    ):
        """
        Initialize base agent
        
        Args:
            verification_id: ID of the verification
            bedrock_client: Deprecated - kept for compatibility
            db_client: Database client
            persona_client: Persona client
            sift_client: Sift client
        """
        self.verification_id = verification_id
        self.db_client = db_client
        self.persona_client = persona_client
        self.sift_client = sift_client
        self.logger = get_logger(self.__class__.__name__)

    async def run(self) -> Dict[str, Any]:
        """
        Execute the agent's primary task
        
        This method should be implemented by subclasses
        
        Returns:
            Dict containing agent results
        """
        try:
            # Implement in subclasses
            raise NotImplementedError("Agent run() method must be implemented by subclasses")
        except Exception as e:
            self.logger.error(f"Agent error: {str(e)}")
            return {
                "agent_type": self.__class__.__name__,
                "status": "error",
                "details": f"Error during execution: {str(e)}",
                "checks": []
            }

    async def extract_data_with_llm(
        self, 
        data: Dict[str, Any], 
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Use Bedrock LLM to extract and analyze data
        
        Args:
            data: Data to analyze
            prompt: Prompt for LLM
            
        Returns:
            Dict containing extraction results
        """
        try:
            # Convert dates to strings for JSON serialization
            json_safe_data = convert_dates_to_strings(data)
            
            # Format the prompt for the LLM
            formatted_prompt = self._format_llm_prompt(json_safe_data, prompt)
            
            # Use connection pool to get client
            async with connection_pool.get_client("bedrock") as bedrock_client:
                response = await bedrock_client.extract_structured_data(
                    data=json_safe_data,
                    extraction_instructions=prompt,
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM extraction error: {str(e)}")
            raise AgentExecutionError(f"LLM extraction error: {str(e)}")

    def _format_llm_prompt(self, data: Dict[str, Any], prompt: str) -> str:
        """
        Format data and prompt for LLM processing
        
        Args:
            data: Data to analyze
            prompt: Prompt for LLM
            
        Returns:
            Formatted prompt
        """
        return f"""
        You are a data extraction expert. Extract the required information based on the following criteria:
        
        {prompt}
        
        Here is the data to analyze:
        {json.dumps(data, indent=2)}
        
        Respond ONLY with a valid JSON object containing the extraction results.
        """
    
    async def get_verification_data(self) -> Dict[str, Any]:
        """
        Get all verification data for this verification
        
        Returns:
            Dict containing verification data
        """
        try:
            verification_data_records = await self.db_client.get_verification_data(self.verification_id)
            
            # Organize data by type
            data = {}
            for record in verification_data_records:
                data_type = record.data_type
                data[data_type] = record.data
                
            return data
        except Exception as e:
            self.logger.error(f"Error getting verification data: {str(e)}")
            raise AgentExecutionError(f"Error getting verification data: {str(e)}")