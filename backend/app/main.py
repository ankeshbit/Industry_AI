"""
Main FastAPI Application for INDUSTRIA AI (PRD v1.2)
Modular monolith SaaS for industrial predictive maintenance.
Pure software implementation: strictly no IoT, MQTT, device code, or hardware streaming.
"""

import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.seed import seed_database
from backend.app.api.auth import router as auth_router, users_router
from backend.app.api.machines import router as machines_router
from backend.app.api.datasets import router as datasets_router
from backend.app.api.compatibility import router as compatibility_router
from backend.app.api.analyses import router as analyses_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.models import router as models_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema and seed tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="INDUSTRIA AI",
    description="PRD v1.2 Compliant Predictive Maintenance Modular Monolith SaaS",
    version="1.2.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized Error Handling (PRD v1.2 §13.1)
# {"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    request_id = str(uuid.uuid4())[:8]
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        error_payload = exc.detail["error"]
        error_payload["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content={"error": error_payload})

    message = exc.detail if isinstance(exc.detail, str) else "An error occurred."
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHENTICATED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "CONFLICT"
    elif exc.status_code == 413:
        code = "PAYLOAD_TOO_LARGE"
    elif exc.status_code == 415:
        code = "UNSUPPORTED_FORMAT"
    elif exc.status_code == 422:
        code = "VALIDATION_ERROR"
    elif exc.status_code == 423:
        code = "ACCOUNT_LOCKED"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(uuid.uuid4())[:8]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": exc.errors(),
                "request_id": request_id
            }
        }
    )

# Include Routers under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(machines_router, prefix=settings.API_V1_PREFIX)
app.include_router(datasets_router, prefix=settings.API_V1_PREFIX)
app.include_router(compatibility_router, prefix=settings.API_V1_PREFIX)
app.include_router(analyses_router, prefix=settings.API_V1_PREFIX)
app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)
app.include_router(models_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "healthy",
        "service": "INDUSTRIA AI",
        "version": "1.2.0"
    }
