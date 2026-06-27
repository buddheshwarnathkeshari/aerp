from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt, JWTError
import bcrypt
from backend.config.settings import get_settings
import redis.asyncio as redis
import structlog

logger = structlog.get_logger()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8')[:72], salt).decode('utf-8')

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    import uuid
    to_encode = {"exp": expire, "sub": str(subject), "jti": str(uuid.uuid4())}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """Decodes a JWT. Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

async def add_token_to_blocklist(jti: str, exp: int):
    """
    Adds a JWT ID (jti) to the Redis blocklist.
    The TTL is set to the remaining time until the token naturally expires.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    ttl = exp - now
    if ttl > 0:
        await redis_client.setex(f"blocklist:{jti}", ttl, "true")
        logger.info("Token added to blocklist", jti=jti, ttl=ttl)

async def is_token_blocked(jti: str) -> bool:
    """Checks if a JWT ID is in the Redis blocklist."""
    if not jti:
        return False
    exists = await redis_client.exists(f"blocklist:{jti}")
    return bool(exists)
