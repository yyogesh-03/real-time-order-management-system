from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError,HTTPException
from app.core.db import init_db, close_db
from app.api.v1.orders import router as orders_router
from app.api.v1.inventory import router as inventory_router
from app.core.config import PROJECT_NAME, VERSION
from app.core.exception_handlers import (
    http_exception_handler,
    setup_exception_handlers,
    validation_exception_handler,
    generic_exception_handler
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    print(f"Starting {PROJECT_NAME} v{VERSION}...")
    await init_db() # Connect to DB and generate schemas
    yield 
    await close_db()
    print(f"{PROJECT_NAME} stopped.")

app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    lifespan=lifespan,
    # Configure API documentation and paths
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers for modular API structure
app.include_router(orders_router, prefix="/api/v1/orders", tags=["Order Management"])
app.include_router(inventory_router, prefix="/api/v1/inventory", tags=["Inventory Utilities"])


setup_exception_handlers(app)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app_name": PROJECT_NAME}