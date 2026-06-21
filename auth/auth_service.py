import os
import secrets
import hashlib
import datetime
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from api.db_models import User, ApiKey, Session as DBSession

# Crypt setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("FATAL: JWT_SECRET_KEY env var not set. Server cannot start.")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: str, department: str, role: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRY_HOURS)
    payload = {
        "sub": str(user_id),
        "dept": department,
        "role": role,
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, db: Session) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise JWTError("Missing subject claim")
            
        # Check session not revoked
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session_record = db.query(DBSession).filter(DBSession.token_hash == token_hash, DBSession.is_revoked == False).first()
        if not session_record:
            raise JWTError("Session revoked or expired")
            
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")

def create_api_key(name: str, department: str, created_by_user_id: str, rate_limit: int, db: Session) -> str:
    dept_slug = department.lower().replace(" ", "_").replace("&", "and")[:3]
    raw_key = f"sk-tn-{dept_slug}-" + secrets.token_hex(16)
    
    # Hash raw key
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    
    # Create record
    new_key = ApiKey(
        key_hash=key_hash,
        name=name,
        department=department,
        created_by_user_id=created_by_user_id,
        rate_limit_per_min=rate_limit,
        is_active=True
    )
    db.add(new_key)
    db.commit()
    
    return raw_key

def verify_api_key(raw_key: str, db: Session) -> dict | None:
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key_record = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True).first()
    
    if not api_key_record:
        return None
        
    # Check expiry
    if api_key_record.expires_at and api_key_record.expires_at < datetime.datetime.utcnow():
        return None
        
    # Update last used
    api_key_record.last_used_at = datetime.datetime.utcnow()
    db.commit()
    
    return {
        "key_hash": api_key_record.key_hash,
        "name": api_key_record.name,
        "department": api_key_record.department,
        "rate_limit_per_min": api_key_record.rate_limit_per_min,
        "allowed_departments": api_key_record.allowed_departments
    }

def change_password(user_id, current_password, new_password, db_session) -> bool:
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found.")
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Incorrect current password.")
    user.hashed_password = hash_password(new_password)
    # Revoke all existing sessions for this user
    db_session.query(DBSession).filter(DBSession.user_id == user_id).update({DBSession.is_revoked: True})
    db_session.commit()
    return True

def create_user(email: str, password: str, full_name: str, organization_name: str, db: Session) -> User:
    # Check if user exists
    if db.query(User).filter(User.email == email).first():
        raise ValueError("User with this email already exists.")
        
    hashed_pw = hash_password(password)
    
    # Create the user with default "free" subscription tier and "b2b_user" role
    new_user = User(
        email=email,
        hashed_password=hashed_pw,
        full_name=full_name,
        organization_name=organization_name,
        role="b2b_user",
        subscription_tier="free",
        api_quota_limit=100,
        api_quota_used=0,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
