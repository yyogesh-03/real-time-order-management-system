from unittest.mock import AsyncMock, MagicMock

# We expose the official AsyncMock as a utility to ensure it has all the
# MagicMock capabilities needed for mocking ORM calls like .prefetch_related.
AsyncMockUtil = AsyncMock

# Mocked Tortoise transaction manager 
class in_transaction:
    """Mock for tortoise.transactions.in_transaction to bypass real DB context."""
    async def __aenter__(self):
        return object() 
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass