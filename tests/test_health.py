import pytest
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health endpoint"""
    from app.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"