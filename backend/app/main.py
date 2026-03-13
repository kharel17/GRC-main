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
    "http://localhost:3001",
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
