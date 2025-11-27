import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID
from app.models.order import OrderStatus
from app.services.order_service import update_order_status
from app.models.order import Order 
from app.models.order import OrderItem 

# --- CORE MOCKING UTILITIES ---

class AsyncContextManagerMock:
    """Mocks 'async with in_transaction() as conn:' to fulfill the async context manager protocol."""
    async def __aenter__(self):
        # Returns a mock connection object 
        return object() 
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

def create_mock_queryset(final_return_value):
    """
    FACTORY: Creates a mock object that supports method chaining like Tortoise ORM.
    Any method called (e.g., prefetch_related, using_db) returns the mock itself,
    and the mock itself is configured to be awaitable, returning the final data.
    This fixes the 'AttributeError: coroutine object has no attribute prefetch_related'.
    """
    # 1. Create a MagicMock to represent the chainable QuerySet
    chainable_mock = MagicMock()
    
    # 2. Configure chaining methods to return the mock object itself
    chainable_mock.prefetch_related.return_value = chainable_mock
    chainable_mock.using_db.return_value = chainable_mock
    
    # 3. Configure the mock to be awaitable (to handle 'await ...')
    async def mock_await():
        return final_return_value
    
    # This configuration makes the entire chained call awaitable, returning the desired object.
    chainable_mock.__await__ = MagicMock(return_value=mock_await().__await__())
    
    return chainable_mock

# --- SETUP FIXTURES (Using the Factory) ---

@pytest.fixture
def mock_order_preparing():
    """Mock Order object in a state that allows forward transition (PREPARING)."""
    mock_order = AsyncMock()
    mock_order.id = UUID("d675f4f3-6c36-46b9-abcf-ba0aa3c60a5e")
    mock_order.user_id = "user-abc"
    mock_order.status = OrderStatus.PREPARING
    mock_order.items = [] 
    mock_order.save = AsyncMock()
    return mock_order

@pytest.fixture
def mock_order_with_items():
    """Mock Order object that includes item data needed for the CANCELLED event payload."""
    mock_order = AsyncMock()
    mock_order.id = UUID("a1b2c3d4-e5f6-7890-abcd-ef0123456789")
    mock_order.user_id = "user-cancel"
    mock_order.status = OrderStatus.PLACED
    
    # Mock related items structure
    MockItem1 = MagicMock(spec=OrderItem)
    MockItem1.menu_item_id = UUID("11111111-0000-0000-0000-000000000001")
    MockItem1.quantity = 2
    
    MockItem2 = MagicMock(spec=OrderItem)
    MockItem2.menu_item_id = UUID("22222222-0000-0000-0000-000000000002")
    MockItem2.quantity = 5
    
    mock_order.items = [MockItem1, MockItem2]
    mock_order.save = AsyncMock()
    return mock_order

@pytest.fixture
def mock_order_final():
    """Mock Order object in a final state (DELIVERED) that should block transitions."""
    mock_order = AsyncMock()
    mock_order.id = UUID("f0e9d8c7-b6a5-4321-fedc-ba9876543210")
    mock_order.status = OrderStatus.DELIVERED
    mock_order.items = []
    mock_order.save = AsyncMock()
    return mock_order

# --- TESTS ---

@pytest.mark.asyncio
@patch('app.services.order_service.in_transaction', new_callable=MagicMock) 
@patch('app.services.order_service.create_outbox_event', new_callable=AsyncMock)
async def test_successful_status_transition(mock_outbox_event, mock_in_transaction, mock_order_preparing):
    """
    Test case 1: Successful state change from PREPARING to OUT_FOR_DELIVERY.
    """
    # Use the factory to create a mock that handles the ORM method chaining.
    mock_queryset = create_mock_queryset(mock_order_preparing)
    
    with patch.object(Order, 'get_or_none', MagicMock(return_value=mock_queryset)):
        
        # Configure the transaction mock
        mock_in_transaction.return_value = AsyncContextManagerMock()

        new_status = OrderStatus.OUT_FOR_DELIVERY
        updated_order = await update_order_status(mock_order_preparing.id, new_status)

        assert updated_order.status == new_status
        mock_order_preparing.save.assert_called_once()
        mock_outbox_event.assert_called_once()
        
        args, kwargs = mock_outbox_event.call_args
        assert kwargs['event_type'] == "order.status.out_for_delivery.v1"


@pytest.mark.asyncio
@patch('app.services.order_service.in_transaction', new_callable=MagicMock) 
@patch('app.services.order_service.create_outbox_event', new_callable=AsyncMock)
async def test_compensation_event_on_cancellation(mock_outbox_event, mock_in_transaction, mock_order_with_items):
    """
    Test case 2: State change to CANCELLED, verifying the compensation event payload.
    """
    # Use the factory to create a mock that handles the ORM method chaining.
    mock_queryset = create_mock_queryset(mock_order_with_items)
    
    with patch.object(Order, 'get_or_none', MagicMock(return_value=mock_queryset)):
        
        # Configure the transaction mock
        mock_in_transaction.return_value = AsyncContextManagerMock()
        
        new_status = OrderStatus.CANCELLED
        updated_order = await update_order_status(mock_order_with_items.id, new_status)

        assert updated_order.status == new_status
        mock_outbox_event.assert_called_once()
        args, kwargs = mock_outbox_event.call_args
        
        assert kwargs['event_type'] == "order.cancelled.v1"
        
        payload_items = kwargs['payload']['items']
        assert len(payload_items) == 2


@pytest.mark.asyncio
@patch('app.services.order_service.in_transaction', new_callable=MagicMock) 
@patch('app.services.order_service.create_outbox_event', new_callable=AsyncMock)
async def test_rejection_of_final_state_transition(mock_outbox_event, mock_in_transaction, mock_order_final):
    """
    Test case 3: Attempting to update status when the order is DELIVERED.
    Verifies a ValueError is raised and no DB/Event operations occur.
    """
    # Use the factory to create a mock that handles the ORM method chaining.
    mock_queryset = create_mock_queryset(mock_order_final)
    
    with patch.object(Order, 'get_or_none', MagicMock(return_value=mock_queryset)):
        
        # Configure the transaction mock
        mock_in_transaction.return_value = AsyncContextManagerMock()

        new_status = OrderStatus.PREPARING 
        
        with pytest.raises(ValueError) as excinfo:
            await update_order_status(mock_order_final.id, new_status)
        
        assert "final state" in str(excinfo.value)
        
        mock_order_final.save.assert_not_called()
        mock_outbox_event.assert_not_called()