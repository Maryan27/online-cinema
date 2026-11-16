from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.controllers import auth, catalog, subscription

from app.controllers import auth, catalog
from app.services.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
    ServiceError,
)

app = FastAPI(
    title="Online Cinema API",
    description="REST API for an online cinema (coursework, variant 17)",
    version="0.1.0",
)

# Maps business-logic errors to HTTP status codes in one place
ERROR_STATUS_CODES = {
    NotFoundError: 404,
    AlreadyExistsError: 409,
    AuthenticationError: 401,
    PermissionDeniedError: 403,
    BusinessRuleError: 400,
}


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError):
    status_code = next(
        (code for error, code in ERROR_STATUS_CODES.items() if isinstance(exc, error)), 400
    )
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


app.include_router(auth.router)
app.include_router(catalog.router)


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok"}

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(subscription.router)