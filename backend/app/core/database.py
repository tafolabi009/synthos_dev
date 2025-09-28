"""
Synthos Database Configuration
Enterprise-grade database setup with connection pooling and migrations
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from fastapi import HTTPException
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Cloud SQL Connector (optional)
try:
    from google.cloud.sql.connector import Connector, IPTypes
except Exception:  # pragma: no cover
    Connector = None
    IPTypes = None

# Update the database URL to use psycopg2 sync dialect
def get_sync_database_url(url: str) -> str:
    """Convert database URL to use psycopg2 sync dialect"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://")
    return url


def get_async_database_url(url: str) -> str:
    """Convert database URL to use asyncpg dialect"""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif url.startswith("sqlite://"):
        # Use aiosqlite driver for async SQLite connections
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    return url


def _make_connector_sync_creator():
    """Returns a connection creator for SQLAlchemy using Cloud SQL Connector (pg8000)."""
    if not Connector or not settings.CLOUDSQL_INSTANCE:
        return None

    connector = Connector()

    def getconn():
        # Ensure password is properly encoded for Cloud SQL Connector
        password = settings.DB_PASSWORD
        if password:
            # Handle special characters in password
            import urllib.parse
            password = urllib.parse.quote_plus(password)
        
        try:
            return connector.connect(
                settings.CLOUDSQL_INSTANCE,
                "pg8000",
                user=settings.DB_USER,
                password=password,
                db=settings.DB_NAME,
                ip_type=IPTypes.PUBLIC,
            )
        except Exception as e:
            logger.error("Cloud SQL Connector connection failed", error=str(e))
            raise

    return getconn


def _make_connector_async_creator():
    """Return SQLAlchemy async creator using Cloud SQL Connector (asyncpg)."""
    if not Connector or not settings.CLOUDSQL_INSTANCE:
        return None

    connector = Connector()

    async def getconn():
        # Ensure password is properly encoded for Cloud SQL Connector
        password = settings.DB_PASSWORD
        if password:
            # Handle special characters in password
            import urllib.parse
            password = urllib.parse.quote_plus(password)
        
        try:
            return await connector.connect_async(
                settings.CLOUDSQL_INSTANCE,
                "asyncpg",
                user=settings.DB_USER,
                password=password,
                db=settings.DB_NAME,
                ip_type=IPTypes.PUBLIC,
            )
        except Exception as e:
            logger.error("Cloud SQL Connector async connection failed", error=str(e))
            raise

    return getconn


# Decide engine strategy
use_connector = bool(settings.USE_CLOUD_SQL_CONNECTOR and settings.CLOUDSQL_INSTANCE and settings.DB_USER and settings.DB_PASSWORD and settings.DB_NAME)

# Try Cloud SQL Connector first, fallback to direct connection
try:
    if use_connector and Connector:
        logger.info("Attempting to use Cloud SQL Connector")
        # Sync engine via connector (pg8000)
        engine = create_engine(
            "postgresql+pg8000://",  # empty URL; use creator
            creator=_make_connector_sync_creator(),
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )

        # Async engine via connector (asyncpg)
        async_engine = create_async_engine(
            "postgresql+asyncpg://",
            creator=_make_connector_async_creator(),
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        logger.info("Cloud SQL Connector engines created successfully")
    else:
        raise Exception("Cloud SQL Connector not configured")
        
except Exception as e:
    logger.warning("Cloud SQL Connector failed, falling back to direct connection", error=str(e))
    # Fallback to raw DATABASE_URL
    engine = create_engine(
        get_sync_database_url(settings.DATABASE_CONNECTION_URL),
        poolclass=QueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # Validates connections before use
        echo=settings.DEBUG,  # Log SQL queries in debug mode
    )

    # Async engine for health checks
    async_engine = create_async_engine(
        get_async_database_url(settings.DATABASE_CONNECTION_URL),
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )
    logger.info("Direct connection engines created successfully")

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


async def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


def get_db():
    """Database dependency for FastAPI"""
    db = None
    try:
        db = SessionLocal()
        # Test the connection with a simple query
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error("Database connection failed in get_db", error=str(e))
        if db:
            db.close()
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable. Please try again later."
        )
    finally:
        if db:
            db.close()


@asynccontextmanager
async def get_db_session():
    """Async database session context manager for health checks"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def check_connection() -> bool:
        """Check database connectivity"""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database connection failed", error=str(e))
            return False
    
    @staticmethod
    def get_db_info() -> dict:
        """Get database information"""
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT version() as version, current_database() as database")
                )
                row = result.fetchone()
                return {
                    "status": "connected",
                    "version": row.version if row else "unknown",
                    "database": row.database if row else "unknown",
                    "pool_size": getattr(engine.pool, 'size', lambda: 'unknown')() if hasattr(engine.pool, 'size') else 'unknown',
                    "checked_out": getattr(engine.pool, 'checkedout', lambda: 'unknown')() if hasattr(engine.pool, 'checkedout') else 'unknown',
                }
        except Exception as e:
            logger.error("Failed to get database info", error=str(e))
            return {"status": "error", "error": str(e)}


# Global database manager instance
db_manager = DatabaseManager() 