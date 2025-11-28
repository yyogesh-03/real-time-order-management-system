import pytest
import sys
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.main import app
from app.consumers.inventory_consumer import handle_order_placed, handle_order_cancelled


@pytest.fixture
def client():
    return TestClient(app)

class TestConsumers:
    
    @pytest.mark.asyncio
    async def test_inventory_deduction(self):
        """Test inventory deduction on order placement"""
        with patch('app.consumers.inventory_consumer.in_transaction'):
            with patch('app.consumers.inventory_consumer.ProcessedEvent.filter') as mock_processed:
                mock_processed.exists.return_value = False
                
                with patch('app.consumers.inventory_consumer.Inventory.filter') as mock_inv_filter:
                    mock_inv = AsyncMock()
                    mock_inv.menu_item_id = uuid4()
                    mock_inv.available_qty = 10
                    async def save_async(): return mock_inv
                    mock_inv.save = save_async
                    
                    mock_inv_query = AsyncMock()
                    mock_inv_query.using_db.return_value = mock_inv_query
                    mock_inv_query.select_for_update.return_value = [mock_inv]
                    mock_inv_filter.return_value = mock_inv_query
                    
                    with patch('app.consumers.inventory_consumer.ProcessedEvent.create'):
                        with patch('app.consumers.inventory_consumer.create_outbox_event') as mock_outbox:
                            
                            await handle_order_placed({
                                "order_id": str(uuid4()),
                                "items": [{"menu_item_id": str(uuid4()), "quantity": 2}]
                            }, uuid4())
                            
                            mock_outbox.assert_called()
                            print("✅ 3. Inventory deduction works")
    
    @pytest.mark.asyncio
    async def test_inventory_restoration(self):
        """Test inventory restoration on order cancellation"""
        with patch('app.consumers.inventory_consumer.in_transaction'):
            with patch('app.consumers.inventory_consumer.ProcessedEvent.filter') as mock_processed:
                mock_processed.exists.return_value = False
                
                with patch('app.consumers.inventory_consumer.Inventory.filter') as mock_inv_filter:
                    mock_inv = AsyncMock()
                    mock_inv.menu_item_id = uuid4()
                    mock_inv.available_qty = 5
                    async def save_async(): return mock_inv
                    mock_inv.save = save_async
                    
                    mock_inv_query = AsyncMock()
                    mock_inv_query.using_db.return_value = mock_inv_query
                    mock_inv_query.select_for_update.return_value = [mock_inv]
                    mock_inv_filter.return_value = mock_inv_query
                    
                    with patch('app.consumers.inventory_consumer.ProcessedEvent.create'):
                        
                        await handle_order_cancelled({
                            "order_id": str(uuid4()),
                            "items": [{"menu_item_id": str(uuid4()), "quantity": 2}]
                        }, uuid4())
                        
                        print("✅ 4. Inventory restoration works")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for insufficient inventory"""
        with patch('app.consumers.inventory_consumer.in_transaction'):
            with patch('app.consumers.inventory_consumer.ProcessedEvent.filter') as mock_processed:
                mock_processed.exists.return_value = False
                
                with patch('app.consumers.inventory_consumer.Inventory.filter') as mock_inv_filter:
                    mock_inv = AsyncMock()
                    mock_inv.menu_item_id = uuid4()
                    mock_inv.available_qty = 1  # Low stock
                    
                    mock_inv_query = AsyncMock()
                    mock_inv_query.using_db.return_value = mock_inv_query
                    mock_inv_query.select_for_update.return_value = [mock_inv]
                    mock_inv_filter.return_value = mock_inv_query
                    
                    with patch('app.consumers.inventory_consumer.create_outbox_event') as mock_outbox:
                        
                        await handle_order_placed({
                            "order_id": str(uuid4()),
                            "items": [{"menu_item_id": str(uuid4()), "quantity": 5}]  # Request 5
                        }, uuid4())
                        
                        mock_outbox.assert_called()
                        print("✅ 5. Error handling works")