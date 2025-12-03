import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from uuid import uuid4

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestOrderRoutes:
    def test_create_order_success(self, client):
        """Test order creation returns 202"""
        with patch('app.api.v1.orders.place_order') as mock_place_order:
            mock_order = AsyncMock()
            mock_order.id = uuid4()
            mock_order.status = "PLACED"
            mock_order.total_amount = "25.98"
            mock_place_order.return_value = mock_order
            
            order_data = {
                "restaurant_id": str(uuid4()),
                "items": [{"menu_item_id": str(uuid4()), "quantity": 1}]
            }
            
            response = client.post("/api/v1/orders", json=order_data)
            assert response.status_code == 202
            assert response.json()["data"]["status"] == "PLACED"
    
    def test_create_order_empty_items(self, client):
        """Test validation for empty items"""
        order_data = {
            "restaurant_id": str(uuid4()),
            "items": []
        }
        
        response = client.post("/api/v1/orders", json=order_data)
        assert response.status_code == 400
    
    def test_get_order_success(self, client):
        """Test order retrieval"""
        with patch('app.api.v1.orders.get_order_by_id') as mock_get_order:
            mock_order = AsyncMock()
            mock_order.id = uuid4()
            mock_order.status = "PLACED"
            mock_order.total_amount = "25.98"
            mock_order.created_at = "2023-10-27T10:30:00"
            mock_order.items = []
            mock_get_order.return_value = mock_order
            
            response = client.get(f"/api/v1/orders/{uuid4()}")
            assert response.status_code == 200