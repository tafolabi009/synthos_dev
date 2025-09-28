"""
Synthos Structured Logging Configuration
Enterprise-grade logging with structured output
"""

import sys
import logging
from typing import Any, Dict
import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == "production":
        # JSON formatting for production
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        # Human-readable formatting for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    
    # Set log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True
    )
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


class ContextualLogger:
    """Logger with automatic context injection"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
    
    def with_context(self, **kwargs: Any) -> structlog.BoundLogger:
        """Add context to logger"""
        return self.logger.bind(**kwargs)
    
    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message with context"""
        self.logger.info(msg, **kwargs)
    
    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message with context"""
        self.logger.error(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message with context"""
        self.logger.warning(msg, **kwargs)
    
    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message with context"""
        self.logger.debug(msg, **kwargs)


def get_logger(name: str) -> ContextualLogger:
    """Get a contextual logger instance"""
    return ContextualLogger(name)


# Audit logging for compliance
class AuditLogger:
    """Specialized logger for audit events"""
    
    def __init__(self):
        self.logger = structlog.get_logger("synthos.audit")
    
    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str = None,
        metadata: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> None:
        """Log user action for audit trail"""
        self.logger.info(
            "User action performed",
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            event_type="user_action",
        )
    
    def log_data_access(
        self,
        user_id: str,
        dataset_id: str,
        access_type: str,
        rows_accessed: int = None,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Log data access events for compliance"""
        self.logger.info(
            "Data access event",
            user_id=user_id,
            dataset_id=dataset_id,
            access_type=access_type,
            rows_accessed=rows_accessed,
            metadata=metadata or {},
            event_type="data_access",
        )
    
    def log_generation_event(
        self,
        user_id: str,
        dataset_id: str,
        rows_generated: int,
        privacy_parameters: Dict[str, Any],
        generation_time: float,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Log synthetic data generation events"""
        self.logger.info(
            "Synthetic data generated",
            user_id=user_id,
            dataset_id=dataset_id,
            rows_generated=rows_generated,
            privacy_parameters=privacy_parameters,
            generation_time=generation_time,
            metadata=metadata or {},
            event_type="data_generation",
        )
    
    def log_privacy_event(
        self,
        user_id: str,
        dataset_id: str,
        privacy_action: str,
        privacy_parameters: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Log privacy-related events for compliance"""
        self.logger.info(
            "Privacy event",
            user_id=user_id,
            dataset_id=dataset_id,
            privacy_action=privacy_action,
            privacy_parameters=privacy_parameters,
            metadata=metadata or {},
            event_type="privacy_event",
        )
    
    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message with context"""
        self.logger.error(msg, **kwargs)
    
    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message with context"""
        self.logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message with context"""
        self.logger.warning(msg, **kwargs)
    
    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message with context"""
        self.logger.debug(msg, **kwargs)


# Global audit logger instance
audit_logger = AuditLogger() 