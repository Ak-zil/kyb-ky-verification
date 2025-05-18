from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class ResultCompilationAgent(BaseAgent):
    """Agent for compiling verification results from all agents"""

    async def run(self) -> Dict[str, Any]:
        """
        Compile verification results from all agents
        
        Returns:
            Dict containing final verification results
        """
        try:
            # Fetch all agent results for this verification
            agent_results = await self.db_client.get_verification_agent_results(self.verification_id)


            # Convert SQLAlchemy models to dictionaries
            agent_results_dicts = []
            for result in agent_results:
                result_dict = {
                    "agent_type": result.agent_type,
                    "status": result.status,
                    "details": result.details,
                    "checks": result.checks if hasattr(result, 'checks') and result.checks else []
                }
                agent_results_dicts.append(result_dict)
            
            # Organize results by agent type
            organized_results = {}
            for result in agent_results:
                agent_type = result.agent_type
                if agent_type not in organized_results:
                    organized_results[agent_type] = result
            
            # Check if any agents had errors
            errors = [r for r in agent_results if r.status == "error"]
            if errors:
                error_agents = [e.agent_type for e in errors]
                return {
                    "agent_type": "ResultCompilationAgent",
                    "status": "error",
                    "details": f"Errors occurred in agents: {', '.join(error_agents)}",
                    "verification_result": "failed",
                    "reasoning": "Cannot complete verification due to errors in processing",
                    "agent_results": agent_results
                }
            
            # Use LLM to analyze all results and make a final determination
            verification_analysis = await self.extract_data_with_llm(
                data={"agent_results": agent_results_dicts},
                prompt="""
                You are a verification expert. Analyze the results from all verification agents and determine:
                1. The overall verification result (passed/failed)
                2. A detailed explanation of your reasoning
                3. Key risk factors identified
                4. Confidence level in your determination
                
                Respond with a JSON object containing these fields:
                - verification_result: "passed" or "failed"
                - reasoning: detailed explanation
                - risk_factors: array of identified risk factors
                - confidence: "low", "medium", or "high"
                - summary: brief overall assessment
                """
            )
            
            # Extract the key determination
            verification_result = verification_analysis.get("verification_result", "failed")
            reasoning = verification_analysis.get("reasoning", "Insufficient data to complete verification")
            
            return {
                "agent_type": "ResultCompilationAgent",
                "status": "success",
                "details": "Successfully compiled verification results",
                "verification_result": verification_result,
                "reasoning": reasoning,
                "risk_factors": verification_analysis.get("risk_factors", []),
                "confidence": verification_analysis.get("confidence", "medium"),
                "agent_results": agent_results
            }
            
        except Exception as e:
            self.logger.error(f"Result compilation error: {str(e)}")
            return {
                "agent_type": "ResultCompilationAgent",
                "status": "error",
                "details": f"Error during result compilation: {str(e)}",
                "verification_result": "failed",
                "reasoning": f"Error during compilation: {str(e)}"
            }


class BusinessResultCompilationAgent(BaseAgent):
    """Agent for compiling business verification results including UBO verifications"""

    def __init__(
        self,
        verification_id: str,
        ubo_verification_ids: List[str] = None,
        **kwargs
    ):
        """
        Initialize business result compilation agent
        
        Args:
            verification_id: ID of the business verification
            ubo_verification_ids: List of UBO verification IDs
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(verification_id=verification_id, **kwargs)
        self.ubo_verification_ids = ubo_verification_ids or []

    async def run(self) -> Dict[str, Any]:
        """
        Compile business verification results including UBO verifications
        
        Returns:
            Dict containing final verification results
        """
        try:
            # Fetch all agent results for business verification
            business_agent_results = await self.db_client.get_verification_agent_results(self.verification_id)
            
            # Convert SQLAlchemy models to dictionaries
            business_agent_results_dicts = []
            for result in business_agent_results:
                result_dict = {
                    "agent_type": result.agent_type,
                    "status": result.status,
                    "details": result.details,
                    "checks": result.checks if result.checks else []
                }
                business_agent_results_dicts.append(result_dict)
            
            # Fetch UBO verification results
            ubo_results = []
            for ubo_verification_id in self.ubo_verification_ids:
                # Get verification
                verification = await self.db_client.get_verification(ubo_verification_id)
                
                # Get final result
                ubo_agent_results = await self.db_client.get_verification_agent_results(ubo_verification_id)
                
                # Find the ResultCompilationAgent result
                ubo_final_result = next((r for r in ubo_agent_results 
                                    if r.agent_type == "ResultCompilationAgent"), None)
                
                ubo_results.append({
                    "verification_id": ubo_verification_id,
                    "status": verification.status if verification else "unknown",
                    "result": ubo_final_result.verification_result if ubo_final_result else None,
                    "reasoning": ubo_final_result.reasoning if ubo_final_result else None
                })
            
            # Check if any business agents had errors
            business_errors = [r for r in business_agent_results if r.status == "error"]
            if business_errors:
                error_agents = [e.agent_type for e in business_errors]
                return {
                    "agent_type": "BusinessResultCompilationAgent",
                    "status": "error",
                    "details": f"Errors occurred in business agents: {', '.join(error_agents)}",
                    "verification_result": "failed",
                    "reasoning": "Cannot complete business verification due to errors in processing",
                    "business_agent_results": business_agent_results_dicts,
                    "ubo_results": ubo_results
                }
            
            # Use LLM to analyze all results and make a final determination
            verification_analysis = await self.extract_data_with_llm(
                data={
                    "business_agent_results": business_agent_results_dicts,
                    "ubo_results": ubo_results,
                    "failed_ubo_verifications": len([r for r in ubo_results if r.get("result") == "failed"])
                },
                prompt="""
                You are a business verification expert. Analyze the results from all business verification agents 
                and UBO verifications to determine:
                1. The overall business verification result (passed/failed)
                2. A detailed explanation of your reasoning
                3. Key risk factors identified
                4. Confidence level in your determination
                
                Important considerations:
                - If any UBO verification failed, consider this in your assessment
                - Weight business structure and ownership verification heavily
                - Consider industry and geographic risk factors
                
                Respond with a JSON object containing these fields:
                - verification_result: "passed" or "failed"
                - reasoning: detailed explanation
                - risk_factors: array of identified risk factors
                - confidence: "low", "medium", or "high"
                - summary: brief overall assessment
                """
            )
            
            # Extract the key determination
            verification_result = verification_analysis.get("verification_result", "failed")
            reasoning = verification_analysis.get("reasoning", "Insufficient data to complete verification")
            
            return {
                "agent_type": "BusinessResultCompilationAgent",
                "status": "success",
                "details": "Successfully compiled business verification results",
                "verification_result": verification_result,
                "reasoning": reasoning,
                "risk_factors": verification_analysis.get("risk_factors", []),
                "confidence": verification_analysis.get("confidence", "medium"),
                "business_agent_results": business_agent_results_dicts,
                "ubo_results": ubo_results
            }
            
        except Exception as e:
            self.logger.error(f"Business result compilation error: {str(e)}")
            return {
                "agent_type": "BusinessResultCompilationAgent",
                "status": "error",
                "details": f"Error during business result compilation: {str(e)}",
                "verification_result": "failed",
                "reasoning": f"Error during compilation: {str(e)}"
            }
        


