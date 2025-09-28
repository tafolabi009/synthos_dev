"""
Synthos Security Module
Advanced security utilities for authentication and authorization
"""

import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from passlib.context import CryptContext
from passlib.hash import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing context with explicit backend configuration
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__default_rounds=12,
    bcrypt__min_rounds=10,
    bcrypt__max_rounds=15
)

# Token serializer for secure tokens
token_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        return None


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt with fallback"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error("Bcrypt hashing failed, using fallback", error=str(e))
        # Fallback to a simpler hashing method if bcrypt fails
        import hashlib
        import secrets
        salt = secrets.token_hex(16)
        return f"sha256${salt}${hashlib.sha256((password + salt).encode()).hexdigest()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash with fallback support"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning("Bcrypt verification failed, trying fallback", error=str(e))
        # Handle fallback hash format
        if hashed_password.startswith("sha256$"):
            try:
                parts = hashed_password.split("$")
                if len(parts) == 3:
                    salt = parts[1]
                    stored_hash = parts[2]
                    import hashlib
                    computed_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
                    return computed_hash == stored_hash
            except Exception as fallback_error:
                logger.error("Fallback verification failed", error=str(fallback_error))
        return False


def generate_password_reset_token(email: str) -> str:
    """Generate secure password reset token"""
    return token_serializer.dumps(
        {"email": email, "purpose": "password_reset"},
        salt="password-reset"
    )


def verify_password_reset_token(token: str, max_age: int = 3600) -> Optional[str]:
    """Verify password reset token and return email"""
    try:
        data = token_serializer.loads(
            token,
            salt="password-reset",
            max_age=max_age
        )
        return data.get("email")
    except (BadSignature, SignatureExpired) as e:
        logger.warning("Invalid or expired password reset token", error=str(e))
        return None


def generate_email_verification_token(email: str) -> str:
    """Generate secure email verification token"""
    return token_serializer.dumps(
        {"email": email, "purpose": "email_verification"},
        salt="email-verification"
    )


def verify_email_verification_token(token: str, max_age: int = 86400) -> Optional[str]:
    """Verify email verification token and return email"""
    try:
        data = token_serializer.loads(
            token,
            salt="email-verification",
            max_age=max_age
        )
        return data.get("email")
    except (BadSignature, SignatureExpired) as e:
        logger.warning("Invalid or expired email verification token", error=str(e))
        return None


def generate_api_key() -> str:
    """Generate secure API key"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify API key against hash"""
    return hash_api_key(plain_key) == hashed_key


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)


def constant_time_compare(a: str, b: str) -> bool:
    """Constant time string comparison to prevent timing attacks"""
    return secrets.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


class SecurityUtils:
    """Advanced security utilities"""
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength and return analysis"""
        analysis = {
            "valid": True,
            "score": 0,
            "issues": [],
            "suggestions": []
        }
        
        # Length check
        if len(password) < 8:
            analysis["valid"] = False
            analysis["issues"].append("Password must be at least 8 characters")
        else:
            analysis["score"] += 1
        
        # Character variety checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_upper:
            analysis["issues"].append("Password should contain uppercase letters")
        else:
            analysis["score"] += 1
            
        if not has_lower:
            analysis["issues"].append("Password should contain lowercase letters")
        else:
            analysis["score"] += 1
            
        if not has_digit:
            analysis["issues"].append("Password should contain numbers")
        else:
            analysis["score"] += 1
            
        if not has_special:
            analysis["issues"].append("Password should contain special characters")
        else:
            analysis["score"] += 1
        
        # Common patterns check
        common_patterns = ["123", "abc", "password", "qwerty"]
        if any(pattern in password.lower() for pattern in common_patterns):
            analysis["issues"].append("Password contains common patterns")
            analysis["score"] -= 1
        
        # Set overall validity
        if analysis["score"] < 3:
            analysis["valid"] = False
        
        return analysis
    
    @staticmethod
    def sanitize_input(input_str: str, max_length: int = 1000) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not isinstance(input_str, str):
            return ""
        
        # Truncate to max length
        sanitized = input_str[:max_length]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\0', '\r', '\n']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        return sanitized.strip()
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_csrf_token(token: str, session_token: str) -> bool:
        """Verify CSRF token"""
        return constant_time_compare(token, session_token)


# Global security utils instance
security_utils = SecurityUtils() 