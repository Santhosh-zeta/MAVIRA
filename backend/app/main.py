from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.core import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal
from app.services.methodology.loader import sync_file_version

configure_logging()
log = get_logger("mavira")
settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.db.session import engine, Base
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        sync_file_version(db)
        db.commit()
    log.info("MAVIRA started", extra={"status": settings.osint_mode})
    yield


app = FastAPI(lifespan=lifespan, title="MAVIRA — Meridian AI Vendor Intelligence & Risk Assessment", version="1.0.0",
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                   allow_methods=["GET", "POST", "PUT"], allow_headers=["Content-Type", "X-API-Key", "X-Analyst", "X-User-Role"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    fields = [".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()]
    return JSONResponse({"error": "Invalid request", "fields": fields}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    ref = uuid.uuid4().hex[:10]
    log.exception("unhandled error", extra={"error": ref})
    return JSONResponse({"error": "Internal error", "reference": ref}, status_code=500)


app.include_router(router)
