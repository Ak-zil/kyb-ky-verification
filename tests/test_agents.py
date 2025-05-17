import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.agents.base import BaseAgent
from app.utils.llm import BedrockClient


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """Test BaseAgent initialization"""
    # Create mock dependencies
    mock_bedrock_client = MagicMock(spec=BedrockClient)
    mock_db_client = MagicMock()
    mock_persona_client = MagicMock()
    mock_sift_client = MagicMock()
    
    # Initialize BaseAgent
    agent = BaseAgent(
        verification_id="test_verification_id",
        bedrock_client=mock_bedrock_client,
        db_client=mock_db_client,
        persona_client=mock_persona_client,
        sift_client=mock_sift_client
    )
    
    # Assert agent properties
    assert agent.verification_id == "test_verification_id"
    assert agent.bedrock_client == mock_bedrock_client
    assert agent.db_client == mock_db_client
    assert agent.persona_client == mock_persona_client
    assert agent.sift_client == mock_sift_client


@pytest.mark.asyncio
async def test_base_agent_run_not_implemented():
    """Test BaseAgent run method raises NotImplementedError"""
    agent = BaseAgent(verification_id="test_verification_id")
    
    with pytest.raises(NotImplementedError):
        await agent.run()


@pytest.mark.asyncio
async def test_base_agent_extract_data_with_llm():
    """Test BaseAgent extract_data_with_llm method"""
    # Create mock dependencies
    mock_bedrock_client = MagicMock(spec=BedrockClient)
    mock_bedrock_client.extract_structured_data = AsyncMock(return_value={
        "analysis": "Test analysis",
        "risk_level": "low"
    })
    
    # Initialize BaseAgent
    agent = BaseAgent(
        verification_id="test_verification_id",
        bedrock_client=mock_bedrock_client
    )
    
    # Test extract_data_with_llm method
    data = {"test": "data"}
    prompt = "Test prompt"
    result = await agent.extract_data_with_llm(data, prompt)
    
    # Assert result
    assert result == {"analysis": "Test analysis", "risk_level": "low"}
    
    # Assert bedrock_client.extract_structured_data was called with correct arguments
    mock_bedrock_client.extract_structured_data.assert_called_once_with(
        data=data,
        extraction_instructions=prompt,
        model_id="anthropic.claude-3-sonnet-20240229-v1:0"
    )


@pytest.mark.asyncio
async def test_base_agent_format_llm_prompt():
    """Test BaseAgent _format_llm_prompt method"""
    agent = BaseAgent(verification_id="test_verification_id")
    
    # Test _format_llm_prompt method
    data = {"test": "data"}
    prompt = "Test prompt"
    formatted_prompt = agent._format_llm_prompt(data, prompt)
    
    # Assert formatted prompt contains the data and prompt
    assert "Test prompt" in formatted_prompt
    assert json.dumps(data, indent=2) in formatted_prompt