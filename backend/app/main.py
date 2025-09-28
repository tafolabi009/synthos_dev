"""
Synthos - Enterprise Synthetic Data Platform
Main FastAPI application entry point with advanced security and performance optimizations
"""

import logging
import asyncio
import structlog
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
import warnings
import pydantic

# Conditional imports for monitoring
try:
    from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import api_router
from app.core.database import create_tables
from app.core.redis import init_redis, get_redis_client
from app.services.auth import AuthService

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

# Suppress Pydantic model namespace warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

# Prometheus metrics (conditional)
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
    REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
    ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
else:
    # Mock metrics for when Prometheus is not available
    class MockMetric:
        def inc(self): pass
        def observe(self, value): pass
        def labels(self, **kwargs): return self
    
    REQUEST_COUNT = MockMetric()
    REQUEST_DURATION = MockMetric()
    ACTIVE_CONNECTIONS = MockMetric()
if PROMETHEUS_AVAILABLE:
    AI_GENERATION_DURATION = Histogram('ai_generation_duration_seconds', 'AI generation duration')
    DATA_QUALITY_SCORE = Gauge('data_quality_score', 'Average data quality score')
else:
    AI_GENERATION_DURATION = MockMetric()
    DATA_QUALITY_SCORE = MockMetric()

# Rate limiting with Redis backend (feature-flagged, disabled in MVP mode)
limiter = None
try:
    if not settings.MVP_MODE and settings.ENABLE_RATE_LIMITING and settings.ENABLE_CACHING:
        limiter = Limiter(key_func=get_remote_address, storage_uri=settings.CACHE_URL)
except Exception:
    limiter = None

# Sentry integration for error tracking (feature-flagged, disabled in MVP mode)
if not settings.MVP_MODE and settings.ENABLE_SENTRY and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(auto_enable=True)],
        traces_sample_rate=0.1,  # Lower sample rate for production
        profiles_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        attach_stacktrace=True,
        send_default_pii=False,  # Privacy compliance
    )

# Enhanced Security headers middleware with MITM protection
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Core security headers (always applied)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        
        # Content Security Policy - prevents injection attacks
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://checkout.paddle.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com https://checkout.paddle.com wss:; "
            "frame-src https://js.stripe.com https://checkout.paddle.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        # HTTPS enforcement headers
        if settings.ENVIRONMENT == "production" or settings.FORCE_HTTPS:
            # Strict Transport Security with preload
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
            
            # Expect-CT header for certificate transparency
            response.headers["Expect-CT"] = "max-age=86400, enforce"
            
            # HTTP Public Key Pinning (if configured)
            if settings.HPKP_PINS:
                response.headers["Public-Key-Pins"] = f"pin-sha256=\"{settings.HPKP_PINS}\"; max-age=2592000; includeSubDomains"
        
        # Additional security headers for all environments
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Remove server information headers
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        return response

# HTTPS enforcement middleware for production and staging
class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip HTTPS enforcement for health checks and metrics
        if request.url.path in ["/health", "/health/ready", "/health/live", "/metrics"]:
            return await call_next(request)
        
        # Enforce HTTPS in production and staging environments
        if settings.ENVIRONMENT in ["production", "staging"] or settings.FORCE_HTTPS:
            # Check if request is over HTTP
            forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
            scheme = request.url.scheme.lower()
            
            if scheme == "http" and forwarded_proto != "https":
                # Redirect to HTTPS
                https_url = request.url.replace(scheme="https")
                return JSONResponse(
                    status_code=status.HTTP_426_UPGRADE_REQUIRED,
                    content={
                        "error": "HTTPS Required",
                        "message": "This service requires HTTPS for security. Please use HTTPS.",
                        "upgrade_to": str(https_url)
                    },
                    headers={
                        "Upgrade": "TLS/1.2, HTTP/1.1",
                        "Connection": "Upgrade",
                        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload"
                    }
                )
        
        return await call_next(request)

# Performance monitoring middleware
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_DURATION.observe(duration)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
        
        finally:
            ACTIVE_CONNECTIONS.dec()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with health checks"""
    # Startup
    logger.info("Starting Synthos platform...")
    
    db_initialized: bool = False
    redis_initialized: bool = False
    ai_warmup_ok: bool = False
    
    try:
        # Initialize database with retry logic
        for attempt in range(3):
            try:
                # Skip table creation since tables already exist
                # await create_tables()
                db_initialized = True
                break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...", error=str(e))
                await asyncio.sleep(2)
        

        # Initialize Redis with connection pooling (only if caching is enabled)
        if settings.ENABLE_CACHING:
            from app.core.redis import init_redis
            await init_redis()

        # Initialize Redis with connection pooling (best-effort)
        try:
            from app.core.redis import init_redis
            await init_redis()
            redis_initialized = True
        except Exception as e:
            logger.warning("Redis initialization failed; continuing in degraded mode", error=str(e))

        
        # Warm up critical services (best-effort)
        try:
            auth_service = AuthService()
            await auth_service.warm_up()
            ai_warmup_ok = True
        except Exception as e:
            logger.warning("Auth/AI warm-up failed; continuing in degraded mode", error=str(e))
        
        logger.info(
            "Synthos platform startup completed",
            db_initialized=db_initialized,
            redis_initialized=redis_initialized,
            ai_warmup_ok=ai_warmup_ok,
        )
        
    except Exception as e:
        # In production/staging, do not crash the service; continue in degraded mode
        if settings.ENVIRONMENT in ["production", "staging"]:
            logger.error("Failed to fully start Synthos platform; continuing in degraded mode", error=str(e), exc_info=True)
        else:
            logger.error("Failed to start Synthos platform", error=str(e), exc_info=True)
            raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Synthos platform...")
    redis_client = await get_redis_client()
    if redis_client:
        await redis_client.close()
    logger.info("Synthos platform shutdown complete")

# Create FastAPI application with enhanced configuration
app = FastAPI(
    title="Synthos API",
    description="Enterprise Synthetic Data Platform with Agentive AI",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    servers=[
        {"url": "/", "description": "Current server"},
        {"url": "https://api.synthos.ai", "description": "Production server"},
    ],
    openapi_tags=[
        {"name": "auth", "description": "Authentication operations"},
        {"name": "datasets", "description": "Dataset management"},
        {"name": "generation", "description": "Synthetic data generation"},
        {"name": "health", "description": "Health check endpoints"},
    ],
)

# Security middleware (order matters!)
# Temporarily disable security middleware for debugging
# app.add_middleware(SecurityHeadersMiddleware)
# app.add_middleware(HTTPSEnforcementMiddleware) # Add HTTPS enforcement middleware
# app.add_middleware(MetricsMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=86400,  # 24 hours
    same_site="strict" if settings.ENVIRONMENT in ["production", "staging"] else "lax",
    https_only=settings.ENVIRONMENT in ["production", "staging"] or getattr(settings, 'FORCE_HTTPS', False)
)

# Trusted host middleware with comprehensive host validation
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS + ["127.0.0.1", "localhost"],
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Response-Time"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Rate limiting
if limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Prometheus metrics endpoint (feature-flagged, disabled in MVP mode)
if not settings.MVP_MODE and getattr(settings, 'ENABLE_PROMETHEUS', False) and PROMETHEUS_AVAILABLE:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# API routes
app.include_router(api_router, prefix="/api/v1")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Enhanced global exception handler with structured logging and correlation IDs"""
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    
    # Log with correlation ID and request context
    logger.error(
        "Global exception occurred",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        user_agent=request.headers.get("User-Agent"),
        client_ip=get_remote_address(request),
        exception=str(exc),
        exc_info=True,
    )
    
    # Don't expose internal errors in production
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "correlation_id": correlation_id,
                "timestamp": time.time()
            }
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    correlation_id = request.headers.get("X-Correlation-ID", "unknown")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }
    )

@app.get("/health", tags=["health"])
async def health_check(request: Request):
    """Enhanced health check with dependency validation"""
    
    checks = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "ai_service": "unknown"
    }
    
    try:
        # Database health check - simple connection test
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"
    
    try:
        # Redis health check (only if caching is enabled)
        if settings.ENABLE_CACHING:
            redis_client = await get_redis_client()
            await redis_client.ping()
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "disabled"
    except Exception:
        checks["redis"] = "unhealthy"
    
    try:
        # AI service health check
        from app.agents.claude_agent import AdvancedClaudeAgent
        agent = AdvancedClaudeAgent()
        await agent.health_check()
        checks["ai_service"] = "healthy"
    except Exception:
        checks["ai_service"] = "unhealthy"
    
    overall_status = "healthy" if all(
        status == "healthy" for status in checks.values()
    ) else "degraded"
    
    return {
        "status": overall_status,
        "service": "synthos-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
        "checks": checks,
        "uptime": time.time() - start_time if 'start_time' in globals() else 0
    }

@app.get("/health/ready", tags=["health"])
async def readiness_check(request: Request):
    """Kubernetes readiness probe"""
    if limiter and not settings.MVP_MODE:
        limiter.limit("10/minute")(readiness_check)
    return {"status": "ready"}

@app.get("/health/live", tags=["health"])
async def liveness_check(request: Request):
    """Kubernetes liveness probe"""
    if limiter and not settings.MVP_MODE:
        limiter.limit("10/minute")(liveness_check)
    return {"status": "alive"}

@app.get("/", tags=["health"])
async def root():
    """Enhanced root endpoint with API discovery"""
    return {
        "message": "Welcome to Synthos - Enterprise Synthetic Data Platform",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api": {
            "docs": "/api/docs" if settings.ENVIRONMENT != "production" else None,
            "health": "/health",
            "metrics": "/metrics",
            "v1": "/api/v1"
        },
        "features": [
            "AI-powered synthetic data generation",
            "Differential privacy protection", 
            "Enterprise-grade security",
            "Real-time generation monitoring",
            "GDPR/CCPA compliance"
        ]
    }

@app.get("/cors-debug", tags=["health"])
async def cors_debug():
    """Debug endpoint to check CORS configuration"""
    return {
        "cors_origins": settings.CORS_ORIGINS,
        "allowed_hosts": settings.ALLOWED_HOSTS,
        "environment": settings.ENVIRONMENT
    }

# Store startup time for uptime calculation
start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.ENVIRONMENT == "development",
        log_config=None,  # Use our structured logging
        workers=1 if settings.ENVIRONMENT == "development" else 4,
        access_log=False,  # Use our custom logging
    ) 