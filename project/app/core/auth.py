"""
Authentication and authorization for the Prescription Authenticator AI system
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.core.config import get_settings
from app.models import User, UserRole, TokenData

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
# Set auto_error to False so we can return 401 instead of the default 403
security = HTTPBearer(auto_error=False)

# Mock user database (in production, use a real database)
USERS_DB: Dict[str, Dict[str, Any]] = {
    "clinician1": {
        "username": "clinician1",
        "email": "clinician1@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "role": UserRole.CLINICIAN,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    "pharmacist1": {
        "username": "pharmacist1",
        "email": "pharmacist1@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "role": UserRole.PHARMACIST,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "role": UserRole.ADMIN,
        "is_active": True,
        "created_at": datetime.utcnow(),
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[User]:
    """Get user from database"""
    user_data = USERS_DB.get(username)
    if user_data:
        return User(**user_data)
    return None


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user_data = USERS_DB.get(username)
    if not user_data:
        logger.warning(f"Authentication failed: user {username} not found")
        return None

    if not verify_password(password, user_data["hashed_password"]):
        logger.warning(f"Authentication failed: invalid password for user {username}")
        return None

    if not user_data["is_active"]:
        logger.warning(f"Authentication failed: user {username} is inactive")
        return None

    logger.info(f"User {username} authenticated successfully")
    return User(**user_data)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify JWT token and return token data"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
        return token_data
    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # If no Authorization header is provided, return 401 (Unauthorized)
    if credentials is None:
        raise credentials_exception

    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(required_role: UserRole):
    """Decorator to require specific user role"""

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role.value} role",
            )
        return current_user

    return role_checker


def require_any_role(*allowed_roles: UserRole):
    """Decorator to require any of the specified roles"""

    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if (
            current_user.role not in allowed_roles
            and current_user.role != UserRole.ADMIN
        ):
            role_names = [role.value for role in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {', '.join(role_names)}",
            )
        return current_user

    return role_checker


# Convenience functions for common role requirements
require_clinician = require_role(UserRole.CLINICIAN)
require_pharmacist = require_role(UserRole.PHARMACIST)
require_admin = require_role(UserRole.ADMIN)
require_clinical_staff = require_any_role(UserRole.CLINICIAN, UserRole.PHARMACIST)
