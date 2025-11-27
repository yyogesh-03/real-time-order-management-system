from tortoise import Tortoise
from app.core.config import DB_URL
import logging
from logging import INFO

# Set logging level for Tortoise ORM
logging.getLogger('tortoise').setLevel(INFO)

# Define all models modules for the ORM
MODELS_MODULES = [
    "app.models.order",
    "app.models.inventory",
    "app.models.outbox",
    "app.models.processed_event",
]

async def init_db():
    """Initializes the Tortoise ORM connection and generates schemas."""
    try:
        await Tortoise.init(
            db_url=DB_URL,
            modules={"models": MODELS_MODULES},
        )
        # Generate the database schema (create tables)
        await Tortoise.generate_schemas()
        print("Database connection established and schemas generated.")
    except Exception as e:
        print(f"FATAL ERROR: Could not connect to database at {DB_URL}. Error: {e}")
        # Re-raise to prevent the application from starting without a database
        raise e 

async def close_db():
    """Closes all database connections."""
    await Tortoise.close_connections()
    print("Database connections closed.")