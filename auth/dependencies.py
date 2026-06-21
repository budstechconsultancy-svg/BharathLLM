from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from api.db_models import User
from .auth_service import verify_token, verify_api_key

# Dependency to get DB session (configured in API server, but placeholder database injector dependency here)
def get_db():
    # Will be overridden in main API lifecycle
    raise NotImplementedError("Database dependency session not attached yet.")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header token format."
        )
    token = authorization.split(" ")[1]
    try:
        payload = verify_token(token, db)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found or inactive.")
        return {
            "user_id": str(user.id),
            "department": user.department,
            "role": user.role,
            "state_code": user.state_code
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

def get_api_key_context(x_api_key: str = Header(None), db: Session = Depends(get_db)) -> dict:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key programmatic access header."
        )
    key_context = verify_api_key(x_api_key, db)
    if not key_context:
        raise HTTPException(status_code=401, detail="Invalid, inactive, or expired API Key.")
    return {
        "key_hash": key_context["key_hash"],
        "department": key_context["department"],
        "role": "api_key",
        "rate_limit": key_context["rate_limit_per_min"],
        "allowed_departments": key_context.get("allowed_departments")
    }

class require_role:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
        
    def __call__(self, user_context: dict = Depends(get_current_user)) -> dict:
        role = user_context.get("role")
        if role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action forbidden for your current authorization scope."
            )
        return user_context

def get_dept_scope(request_context: dict) -> tuple[str, str]:
    # Returns (department_name, Qdrant_collection_name)
    dept = request_context.get("department")
    role = request_context.get("role")
    
    # Collection slug formatting rules
    slug = dept.lower().replace(" ", "_").replace("&", "and")
    collection_name = f"tn_{slug}_docs"
    
    return dept, collection_name
