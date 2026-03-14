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
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AI Service Initialization ─────────────────────────────
from app.services.ai_service import ai_service

@app.on_event("startup")
async def startup_ai_service():
    """Initialize the AI semantic engine on server startup."""
    try:
        ai_service.initialize()
        logger.info("AI Service initialized successfully")
    except Exception as e:
        logger.warning(f"AI Service failed to initialize: {e}. AI endpoints will return 503.")

# ── Platform Team Role Fix ─────────────────────────────────
@app.on_event("startup")
async def fix_platform_team_roles():
    """Ensure platform team accounts always have correct admin roles."""
    from sqlalchemy import select
    from app.database import SessionLocal
    from app import models

    ROLE_OVERRIDE_MAP = {
        "alice@company.com":   models.UserRole.admin,
        "carol@company.com":   models.UserRole.manager,
        "bob@company.com":     models.UserRole.analyst,
        "bcolorc17@gmail.com": models.UserRole.admin,
        "grchelios@gmail.com": models.UserRole.admin,
    }

    try:
        async with SessionLocal() as db:
            # 1. Ensure "Platform Team" organization exists
            platform_org_result = await db.execute(
                select(models.Organization).where(models.Organization.name == "Platform Team")
            )
            platform_org = platform_org_result.scalar_one_or_none()
            
            if not platform_org:
                platform_org = models.Organization(
                    id=uuid.uuid4(),
                    name="Platform Team",
                    onboarding_completed=True
                )
                db.add(platform_org)
                await db.flush()
                logger.info("Created 'Platform Team' organization for system users.")

            # 2. Apply role overrides and sync organizations
            for email, role in ROLE_OVERRIDE_MAP.items():
                result = await db.execute(
                    select(models.User).where(models.User.email == email)
                )
                user = result.scalar_one_or_none()
                if user:
                    needs_update = False
                    if user.role != role:
                        user.role = role
                        needs_update = True
                    if user.invitation_status != 'active':
                        user.invitation_status = 'active'
                        needs_update = True
                    if not user.organization_id:
                        user.organization_id = platform_org.id
                        user.organization_name = platform_org.name
                        needs_update = True
                    
                    if needs_update:
                        await db.flush()
                        logger.info(f"Updated platform user status: {email}")
            
            await db.commit()
    except Exception as e:
        logger.warning(f"Platform team role fix skipped: {e}")


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
