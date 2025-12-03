import uuid
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# Generate a clean request id for every response
def _rid():
    """Generates a unique request ID for tracing."""
    return uuid.uuid4().hex


# ----------- Exception Handlers (called by FastAPI) -----------

def http_exception_handler(request: Request, exc: HTTPException):
    """Handles exceptions raised by HTTPException (e.g., 404, 400)."""
    body = {
        "success": False,
        "error": {
            "code": "http_error",
            "message": exc.detail,
        },
        "request_id": _rid(),
    }
    # Note: No need for 'async' since no awaitable operations are performed inside.
    return JSONResponse(status_code=exc.status_code, content=body)


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors (422 Unprocessable Entity)."""
    body = {
        "success": False,
        "error": {
            "code": "validation_error",
            "message": "Invalid input data",
            "details": exc.errors(),
        },
        "request_id": _rid(),
    }
    # Note: No need for 'async' since no awaitable operations are performed inside.
    return JSONResponse(status_code=422, content=body)


def generic_exception_handler(request: Request, exc: Exception):
    """Handles all unhandled exceptions (500 Internal Server Error)."""
    # Log the full traceback for debugging purposes
    # Note: If you later add async logging (e.g., sending metrics), 
    # you would need to revert this to 'async def' and use 'await'.
    print(f"Unhandled exception on path: {request.url.path}")
    print("Traceback:", traceback.format_exc())

    body = {
        "success": False,
        "error": {
            "code": "server_error",
            "message": "Internal Server Error",
        },
        "request_id": _rid(),
    }
    return JSONResponse(status_code=500, content=body)


# ----------- Registration Function -----------

def setup_exception_handlers(app: FastAPI):
    """Registers all custom exception handlers with the FastAPI application."""
    
    # Register handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    return app