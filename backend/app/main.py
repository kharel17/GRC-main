from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.api.api import api_router
from app.logging_config import setup_logging
import logging
import time
import uuid

# Initialize structured logging
setup_logging()
logger = logging.getLogger("grc")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# ── CORS Origins ───────────────────────────────────────────
allowed_origins = [
    "https://grc-main.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# ── Security Headers Middleware ────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

# ── Request Logging Middleware ─────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Inject request_id for correlation
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    process_time = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": process_time,
            "client_ip": request.client.host if request.client else "unknown",
        }
    )
    response.headers["X-Request-ID"] = request_id
    return response

# ── CORS Middleware (registered last = runs first) ─────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS or allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handler ──────────────────────────────
# Ensures CORS headers are present even on unhandled 500 errors.
# Without this, the browser blocks 500 responses as CORS violations,
# causing "Failed to fetch" instead of showing the actual error.
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    origin = request.headers.get("origin", "")
    headers = {}
    cors_origins = settings.BACKEND_CORS_ORIGINS or allowed_origins
    if origin in cors_origins or "*" in cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers=headers,
    )

# ── AI Service Initialization ─────────────────────────────
from app.services.ai_service import ai_service

import threading

@app.on_event("startup")
async def startup_ai_service():
    """Initialize the AI semantic engine on server startup in background."""
    def run_init():
        try:
            ai_service.initialize()
            logger.info("AI Service initialized successfully in background")
        except Exception as e:
            logger.warning(f"AI Service background initialization failed: {e}. AI endpoints will return 503.")
    
    # Run in a separate thread so it doesn't block the FastAPI startup event
    # and prevents ERR_CONNECTION_REFUSED while the model downloads/loads.
    threading.Thread(target=run_init, daemon=True).start()
    logger.info("AI Service initialization triggered in background thread")

import asyncio

# ── Real User Role Fix ──────────────────────────────────────
@app.on_event("startup")
async def real_user_role_fix_startup():
    """Wrapper to run role fix in background to avoid blocking server startup."""
    asyncio.create_task(fix_real_user_roles())
    logger.info("Real user role fix scheduled in background")

async def fix_real_user_roles():
    """Ensure superadmin accounts belong to the platform team (no customer org) and developer admin accounts are correctly setup."""
    from sqlalchemy import select
    from app.database import SessionLocal
    from app import models

    SUPERADMIN_EMAILS = {
        "grchelios@gmail.com",
        "bcolorc17@gmail.com",
        "grcacc55@gmail.com",
    }

    try:
        async with SessionLocal() as db:
            for email in SUPERADMIN_EMAILS:
                result = await db.execute(
                    select(models.User).where(models.User.email == email)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    needs_update = False
                    if user.role != models.UserRole.superadmin:
                        user.role = models.UserRole.superadmin
                        needs_update = True
                        logger.info(f"Startup check: Fixed role for {email} → superadmin")
                    
                    if user.invitation_status != 'active':
                        user.invitation_status = 'active'
                        needs_update = True
                        logger.info(f"Startup check: Activated user {email}")
                    
                    # Superadmins belong to Platform Team (organization_id is None)
                    if user.organization_id is not None:
                        user.organization_id = None
                        user.organization_name = "Platform Team"
                        needs_update = True
                        logger.info(f"Startup check: Detached superadmin {email} from tenant organization")

                    if needs_update:
                        await db.flush()
            
            await db.commit()
    except Exception as e:
        logger.warning(f"Real user role fix skipped: {e}")


# ── Health Check ───────────────────────────────────────────
@app.get("/health")
async def health_check():
    # Check database connectivity
    db_healthy = False
    try:
        from app.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_healthy = True
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "environment": settings.ENVIRONMENT,
        "ai_ready": ai_service.is_ready,
        "ai_engine": ai_service.active_engine if ai_service.is_ready else "not_initialized",
    }

@app.get("/")
def root():
    return {"message": "Welcome to GRC Platform API"}

# ── Include API Router ─────────────────────────────────────
app.include_router(api_router, prefix=settings.API_V1_STR)
