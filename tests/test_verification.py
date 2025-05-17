import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_start_kyc_verification_api_key_validation(mock_get_api_key, client):
    """Test KYC verification API key validation"""
    # Mock API key validation to raise exception
    mock_get_api_key.side_effect = Exception("Invalid API key")
    
    response = client.post(
        "/api/verify/kyc",
        json={"user_id": "user123"},
        headers={"api-key": "invalid_key"}
    )
    
    assert response.status_code == 500
    assert "Error starting verification" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_start_kyc_verification_validation_error(mock_get_api_key, client):
    """Test KYC verification with validation error"""
    # Mock API key validation to return the key
    mock_get_api_key.return_value = "valid_key"
    
    response = client.post(
        "/api/verify/kyc",
        json={"user_id": ""},  # Empty user_id should fail validation
        headers={"api-key": "valid_key"}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_start_business_verification_api_key_validation(mock_get_api_key, client):
    """Test business verification API key validation"""
    # Mock API key validation to raise exception
    mock_get_api_key.side_effect = Exception("Invalid API key")
    
    response = client.post(
        "/api/verify/business",
        json={"business_id": "business123"},
        headers={"api-key": "invalid_key"}
    )
    
    assert response.status_code == 500
    assert "Error starting verification" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_start_business_verification_validation_error(mock_get_api_key, client):
    """Test business verification with validation error"""
    # Mock API key validation to return the key
    mock_get_api_key.return_value = "valid_key"
    
    response = client.post(
        "/api/verify/business",
        json={"business_id": ""},  # Empty business_id should fail validation
        headers={"api-key": "valid_key"}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_get_verification_status_not_found(mock_get_api_key, client):
    """Test get verification status for non-existent verification"""
    # Mock API key validation to return the key
    mock_get_api_key.return_value = "valid_key"
    
    response = client.get(
        "/api/verify/status/nonexistent_id",
        headers={"api-key": "valid_key"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
@patch("app.services.apikey.get_api_key")
async def test_get_verification_report_missing_ids(mock_get_api_key, client):
    """Test get verification report with missing IDs"""
    # Mock API key validation to return the key
    mock_get_api_key.return_value = "valid_key"
    
    response = client.get(
        "/api/verify/report",
        headers={"api-key": "valid_key"}
    )
    
    assert response.status_code == 400
    assert "Either business_id or user_id must be provided" in response.json()["detail"]