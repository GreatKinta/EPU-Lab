import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import AppError
from app.infrastructure.blockchain.router import router as blockchain_router
from app.modules.ai.router import router as ai_router
from app.modules.borrowing.router import router as borrowing_router
from app.modules.identity.router import router as identity_router
from app.modules.inventory.router import router as inventory_router
from app.modules.reporting.router import router as reporting_router

settings = get_settings()
app = FastAPI(title="LabChain API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(uuid4())
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(AppError)
async def app_error(request, exc):
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Dữ liệu không hợp lệ",
            "details": [
                {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]}
                for e in exc.errors()
            ],
        },
    )


@app.exception_handler(IntegrityError)
async def conflict_error(request, exc):
    return JSONResponse(
        status_code=409,
        content={"code": "CONFLICT", "message": "Dữ liệu trùng hoặc vi phạm ràng buộc"},
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logging.getLogger(__name__).error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={
            "code": "DATABASE_UNAVAILABLE",
            "message": "Cơ sở dữ liệu tạm thời không sẵn sàng",
        },
    )


@app.get("/api/v1/health", tags=["system"])
def health():
    return {"status": "ok", "service": "labchain"}


@app.get("/api/v1/ready", tags=["system"])
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM alembic_version"))
        return {"status": "ready", "database": "ok"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"code": "NOT_READY", "message": "Database or migration unavailable"},
        )


app.include_router(identity_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")

app.include_router(borrowing_router, prefix="/api/v1")
app.include_router(reporting_router, prefix="/api/v1")

app.include_router(blockchain_router, prefix="/api/v1")

app.include_router(ai_router, prefix="/api/v1")
