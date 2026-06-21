import os
import sys
import uuid
import shutil
import hashlib
import logging
import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import torch
from werkzeug.utils import secure_filename


# Import pipeline, auth, and worker modules
from pipeline.query_router import QueryRouter
from api.db_models import Base, User, ApiKey, Session as DBSession
from auth.auth_service import verify_password, create_access_token, create_api_key, change_password, create_user
from auth.dependencies import get_current_user, get_api_key_context, require_role, get_dept_scope
from auth.rate_limiter import check_rate_limit
from workers.tasks import ingest_pdf_task
from workers.job_store import get_job, list_jobs
from agents.supervisor import SupervisorAgent
from api.multimodal_routes import router as multimodal_router
from api.whatsapp_webhook import router as whatsapp_router

# Global state trackers
router_instance: Optional[QueryRouter] = None
supervisor_instance: Optional[SupervisorAgent] = None
engine = None
SessionLocal = None

logger = logging.getLogger("Gateway")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/bharatllm")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://llm.tn.gov.in,https://health.tn.gov.in").split(",")

# DB Session injector dependency mapping
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request Context models
class QueryRequest(BaseModel):
    question: str
    doc_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    top_k: Optional[int] = 5
    override_department: Optional[str] = None

class AgentTaskRequest(BaseModel):
    task: str
    priority: Optional[str] = "normal"

class AgentApproveRequest(BaseModel):
    approved: bool
    edited_parameters: Optional[dict] = None

class LoginRequest(BaseModel):
    employee_id_or_email: str
    password: str

from pydantic import validator

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: Optional[str] = None
    
    # Fix H-3: Exclude password from logs
    model_config = {
        "json_schema_extra": {
            "exclude": {"password"}
        }
    }

    # Fix C-3: Password strength validation
    @validator("password")
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

class SubscriptionUpgradeRequest(BaseModel):
    tier: str  # e.g., "pro", "enterprise"

class ApiKeyRequest(BaseModel):
    name: str
    rate_limit_per_min: Optional[int] = 100
    expires_at: Optional[datetime.date] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

from prometheus_client import Gauge, Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

MODEL_LOADED = Gauge("llm_model_loaded", "Whether fine-tuned model is loaded")
GPU_VRAM_USED = Gauge("llm_gpu_vram_mb", "GPU VRAM used in MB")
QUERY_CONFIDENCE = Histogram("llm_query_confidence", "Query confidence scores",
  buckets=[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0])
DEPT_QUERY_COUNT = Counter("llm_dept_queries_total", "Queries by department",
  labelnames=["department","query_type"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    global router_instance, engine, SessionLocal
    logger.info("Starting FastAPI Gateway Lifespan Setup...")
    
    # 1. Initialize Database configuration
    try:
        # Fix 4.1: Configurable connection pooling for production concurrency
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "30"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        is_sqlite = DATABASE_URL.startswith("sqlite")

        if is_sqlite:
            # SQLite does not support connection pooling the same way
            engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        else:
            engine = create_engine(
                DATABASE_URL,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=1800,    # Recycle connections every 30 minutes
                pool_pre_ping=True    # Health-check connection before using
            )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database engine connected. Pool size: {pool_size}, Max overflow: {max_overflow}.")
    except Exception as e:
        logger.error(f"PostgreSQL Connection failed on startup: {e}")
        
    # 2. Initialize ML Engines
    try:
        model_path = os.getenv("MODEL_NAME")
        router_instance = QueryRouter(model_path=model_path)
        supervisor_instance = SupervisorAgent()
        MODEL_LOADED.set(1)
        logger.info("QueryRouter (LLM + Embedding + Qdrant) successfully loaded in server context.")
        MODEL_LOADED.set(1)
    except Exception as e:
        logger.error(f"Failed to load QueryRouter models during startup (RAG fallback option enabled): {e}")
        router_instance = None
        MODEL_LOADED.set(0)
        
    # Record GPU memory if available
    if torch.cuda.is_available():
        try:
            vram = torch.cuda.memory_allocated() / (1024 * 1024)
            GPU_VRAM_USED.set(vram)
        except Exception:
            GPU_VRAM_USED.set(0)
    else:
        GPU_VRAM_USED.set(0)
        
    yield
    
    # 3. Shutdown cleanup
    logger.info("FastAPI Gateway Lifespan tearing down...")
    MODEL_LOADED.set(0)
    if torch.cuda.is_available():
        logger.info("Clearing CUDA device caches...")
        if router_instance:
            del router_instance
        torch.cuda.empty_cache()
        logger.info("VRAM memory released.")

app = FastAPI(
    title="BharatLLM Unified API",
    version="1.0.0",
    lifespan=lifespan
)

# Mount Routers
app.include_router(multimodal_router)
app.include_router(whatsapp_router)

# Enable Cors checks
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Fix 3.3: Global payload size middleware — reject requests > 20MB
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB

@app.middleware("http")
async def limit_upload_size(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_SIZE:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=413,
            content={"detail": "Request too large. Maximum upload size is 20MB."}
        )
    return await call_next(request)

# Instrument FastAPI app
Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/health", "/metrics"]
).instrument(app).expose(app, endpoint="/metrics")

# Overrides default unimplemented dependency injection in dependencies module
from auth import dependencies
app.dependency_overrides[dependencies.get_db] = get_db

# Resolver dependency: Tries JWT first, falls back to API Key
def get_request_context(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> dict:
    if authorization:
        return get_current_user(authorization=authorization, db=db)
    elif x_api_key:
        return get_api_key_context(x_api_key=x_api_key, db=db)
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication parameters missing. Provide JWT bearer token or X-API-Key."
    )

# ----------------- AUTH ENDPOINTS -----------------

@app.post("/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    try:
        user = create_user(req.email, req.password, req.full_name, req.organization_name, db)
        token = create_access_token(user.id, user.department, user.role)
        
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expire_time = datetime.datetime.utcnow() + datetime.timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", "8")))
        new_session = DBSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expire_time,
            is_revoked=False
        )
        db.add(new_session)
        db.commit()
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "name": user.full_name,
                "role": user.role,
                "subscription_tier": user.subscription_tier
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/auth/subscription")
def get_subscription(context: dict = Depends(get_request_context), db: Session = Depends(get_db)):
    user_id = context.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="API keys cannot query subscriptions.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    return {
        "tier": user.subscription_tier,
        "quota_limit": user.api_quota_limit,
        "quota_used": user.api_quota_used,
        "organization": user.organization_name
    }

@app.post("/auth/subscription/upgrade")
def upgrade_subscription(req: SubscriptionUpgradeRequest, context: dict = Depends(get_request_context), db: Session = Depends(get_db)):
    user_id = context.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="API keys cannot upgrade subscriptions.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if req.tier == "pro":
        user.subscription_tier = "pro"
        user.api_quota_limit = 1000
    elif req.tier == "enterprise":
        user.subscription_tier = "enterprise"
        user.api_quota_limit = 10000
    else:
        raise HTTPException(status_code=400, detail="Invalid tier. Choose 'pro' or 'enterprise'.")

    # Fix 2.3: Revoke all old sessions so stale JWT claims are invalidated
    db.query(DBSession).filter(DBSession.user_id == user_id).update({DBSession.is_revoked: True})
    db.commit()

    # Issue a fresh JWT with updated tier
    new_token = create_access_token(user.id, user.department, user.role)
    token_hash = hashlib.sha256(new_token.encode("utf-8")).hexdigest()
    expire_time = datetime.datetime.utcnow() + datetime.timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", "8")))
    db.add(DBSession(user_id=user.id, token_hash=token_hash, expires_at=expire_time, is_revoked=False))
    db.commit()

    return {
        "message": f"Successfully upgraded to {req.tier} tier.",
        "new_limit": user.api_quota_limit,
        "new_access_token": new_token,
        "token_type": "bearer"
    }

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # Simple brute force limit check (5 requests/min per identifier)
    check_rate_limit(f"login:{req.employee_id_or_email}", max_requests=5, window_seconds=60)
    
    user = db.query(User).filter(User.employee_id == req.employee_id_or_email, User.is_active == True).first()
    if not user:
        user = db.query(User).filter(User.email == req.employee_id_or_email, User.is_active == True).first()
        
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid employee credentials or password.")
        
    token = create_access_token(user.id, user.department, user.role)
    
    # Store session hash in database
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expire_time = datetime.datetime.utcnow() + datetime.timedelta(hours=int(os.getenv("JWT_EXPIRY_HOURS", "8")))
    new_session = DBSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expire_time,
        is_revoked=False
    )
    db.add(new_session)
    
    # Update last login time
    user.last_login = datetime.datetime.utcnow()
    db.commit()
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": user.full_name,
            "department": user.department,
            "role": user.role
        }
    }

@app.post("/auth/logout")
def logout(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
         raise HTTPException(status_code=400, detail="Invalid token header.")
    token = authorization.split(" ")[1]
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    
    session = db.query(DBSession).filter(DBSession.token_hash == token_hash).first()
    if session:
        session.is_revoked = 1
        db.commit()
        
    return {"detail": "Successfully logged out and session revoked."}

@app.post("/auth/change-password")
def change_user_password(
    req: ChangePasswordRequest,
    context: dict = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    if "user_id" not in context:
        raise HTTPException(status_code=403, detail="API keys cannot change user passwords.")
        
    # Requirements check: new_password == confirm_password
    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match.")
        
    # Minimum length 12
    if len(req.new_password) < 12:
        raise HTTPException(status_code=400, detail="New password must be at least 12 characters long.")
        
    # No reuse
    if req.new_password == req.current_password:
        raise HTTPException(status_code=400, detail="New password cannot be the same as the current password.")
        
    # Complexity: uppercase + lowercase + digit + symbol
    if (not any(c.isupper() for c in req.new_password) or
        not any(c.islower() for c in req.new_password) or
        not any(c.isdigit() for c in req.new_password) or
        not any(not c.isalnum() and not c.isspace() for c in req.new_password)):
        raise HTTPException(status_code=400, detail="Password must contain uppercase, lowercase, digit, and symbol.")
        
    try:
        user_id = context["user_id"]
        change_password(user_id, req.current_password, req.new_password, db)
    except ValueError as e:
        raise HTTPException(status_code=401 if "Incorrect" in str(e) else 400, detail=str(e))
        
    return {"message": "Password changed. Please log in again."}

# ----------------- QUERY SYSTEM ENDPOINTS -----------------

@app.post("/query")
def query_system(req: QueryRequest, context: dict = Depends(get_request_context), db: Session = Depends(get_db)):
    from auth.rate_limiter import ROLE_RATE_LIMITS
    role = context.get("role")
    if role == "api_key":
        rate_limit = context.get("rate_limit", ROLE_RATE_LIMITS["api_key"])
    else:
        rate_limit = ROLE_RATE_LIMITS.get(role, 20)
        
    check_rate_limit(f"query:{context.get('user_id', context.get('key_hash'))}", max_requests=rate_limit, window_seconds=60)
    
    if not router_instance:
         raise HTTPException(status_code=503, detail="Document Intelligence Router engine offline. Check logs.")
         
    # Fix 2.1: Atomic quota enforcement — avoids race conditions under concurrent load
    user_id = context.get("user_id")
    if user_id:
        rows_updated = db.query(User).filter(
            User.id == user_id,
            User.role == "b2b_user",
            User.api_quota_used < User.api_quota_limit
        ).update({User.api_quota_used: User.api_quota_used + 1})
        db.commit()
        if rows_updated == 0:
            # Check if user exists and is a b2b_user to give the right error
            chk = db.query(User).filter(User.id == user_id, User.role == "b2b_user").first()
            if chk:
                raise HTTPException(status_code=429, detail=f"Quota exceeded for '{chk.subscription_tier}' tier. Upgrade at /auth/subscription/upgrade.")

    # Fix 2.2: Enforce API key department scoping
    if context.get("role") == "api_key":
        allowed_depts = context.get("allowed_departments")
        if allowed_depts is not None:
            requested_dept = (context.get("department") or "").lower()
            if requested_dept not in [d.lower() for d in allowed_depts]:
                raise HTTPException(
                    status_code=403,
                    detail=f"This API key is scoped to {allowed_depts}. Access to '{requested_dept}' is denied."
                )
         
    # Enforce department scoping rules
    target_dept = context["department"]
    if context["role"] == "super_admin" and req.override_department:
         # super admin override rule
         target_dept = req.override_department
         
    filters = {}
    if req.doc_type:
        filters["doc_type"] = req.doc_type
    if req.date_from:
        filters["date_from"] = req.date_from
    if req.date_to:
        filters["date_to"] = req.date_to
        
    try:
        response = router_instance.route_and_query(req.question, target_dept, filters)
        
        # Log query transaction logs
        logger.info(f"Query executed successfully for {target_dept} (Type: {response['query_type']})")
        
        # Track Prometheus metrics
        QUERY_CONFIDENCE.observe(response.get("confidence", 0.0))
        DEPT_QUERY_COUNT.labels(department=target_dept, query_type=response.get("query_type", "RAG")).inc()
        
        return {
            "answer": response["answer"],
            "query_type": response["query_type"],
            "sources": response["sources"],
            "sql_generated": response["sql_generated"],
            "db_row_count": response["db_row_count"],
            "confidence": response["confidence"],
            "chunks_used": response["chunks_used"],
            "query_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.now().isoformat(),
            "query_language": response["query_language"]
        }
    except Exception as e:
        logger.error(f"Server error during search translation query execution: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error processing query: {str(e)}")

# ----------------- HEALTH ENDPOINT -----------------

@app.get("/health")
def health_check():
    # Simple check to confirm connection to vector DB and models loading
    model_loaded = router_instance is not None
    qdrant_connected = False
    collections = []
    
    if model_loaded:
        try:
            q_client = router_instance.rag_engine.qdrant_client
            # Verify connection
            q_cols = q_client.get_collections()
            qdrant_connected = True
            for col in q_cols.collections:
                status = q_client.get_collection(col.name)
                collections.append({
                    "name": col.name,
                    "vector_count": status.points_count
                })
        except Exception:
            qdrant_connected = False
            
    return {
        "status": "healthy" if (model_loaded and qdrant_connected) else "degraded",
        "model_loaded": model_loaded,
        "model_type": "Fine-Tuned LLaMA 3.1 8B" if model_loaded and "bharatllm-final" in router_instance.rag_engine.tokenizer.name_or_path else "Base LLaMA 3.1 8B",
        "vector_db_connected": qdrant_connected,
        "collections": collections,
        "version": "1.0.0"
    }

# ----------------- INGESTION ENDPOINTS -----------------

@app.post("/ingest")
def upload_document(
    file: UploadFile = File(...),
    context: dict = Depends(get_request_context)
):
    if context.get("role") not in ["dept_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Action forbidden for your current authorization scope.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF file format uploads are allowed.")
        
    # Read uploaded file bytes into memory immediately (before response)
    try:
        content = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")
        
    # Fix H-4: PDF size limit
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF file too large. Maximum upload size is 50MB.")
        
    # Verify magic bytes start with %PDF
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Invalid PDF file headers.")
         
    # Save file to data/raw
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    job_uuid = str(uuid.uuid4())
    saved_filename = f"{job_uuid}_{secure_filename(file.filename)}"
    save_path = raw_dir / saved_filename
    
    try:
        with open(save_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file to disk: {e}")
        
    # Verify saved_path exists and size > 0 before queuing
    if not save_path.exists() or save_path.stat().st_size == 0:
        raise HTTPException(status_code=500, detail="Saved file validation failed.")
        
    # Dispatch Celery background task
    dept = context["department"]
    task = ingest_pdf_task.apply_async(args=[str(save_path), file.filename, dept], task_id=job_uuid)
    
    return {
        "job_id": task.id,
        "status": "queued",
        "filename": file.filename,
        "department": dept,
        "saved_as": saved_filename
    }

@app.get("/ingest/status/{job_id}")
def get_ingest_status(job_id: str, context: dict = Depends(get_request_context)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Ingestion job {job_id} not found.")
        
    # Scope check: user can only see own department ingestion jobs
    if context["role"] != "super_admin" and job["department"] != context["department"]:
        raise HTTPException(status_code=403, detail="Access denied. Cannot view status of other department's job.")
        
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress_pct": job["progress_pct"],
        "step": job["step"],
        "result": job.get("result", None),
        "error": job.get("error", None)
    }

@app.get("/ingest/history")
def get_ingest_history(
    page: int = 1,
    limit: int = 20,
    context: dict = Depends(get_request_context)
):
    if context.get("role") not in ["dept_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Action forbidden for your current authorization scope.")
    target_dept = None if context["role"] == "super_admin" else context["department"]
    jobs = list_jobs(target_dept)
    
    # Simple python sorting of lists
    jobs = sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)
    
    # Paginate list
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    return {
        "total": len(jobs),
        "page": page,
        "limit": limit,
        "results": jobs[start_idx:end_idx]
    }

# ----------------- API KEYS ENDPOINTS -----------------

@app.post("/auth/api-keys")
def generate_scoped_api_key(
    req: ApiKeyRequest,
    context: dict = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    if context.get("role") not in ["dept_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Action forbidden for your current authorization scope.")
    # Generates programmatic key scoped to owner department
    try:
        raw_key = create_api_key(
            name=req.name,
            department=context["department"],
            created_by_user_id=context["user_id"],
            rate_limit=req.rate_limit_per_min,
            db=db
        )
        return {
            "name": req.name,
            "api_key": raw_key,
            "department": context["department"],
            "rate_limit_per_min": req.rate_limit_per_min,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "warning": "Copy this API key now. It will not be shown again."
        }
    except Exception as e:
        logger.error(f"Failed to generate API Key: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate scoped key.")


# ----------------- AGENT ENDPOINTS -----------------

@app.post("/agent/task")
async def agent_task(req: AgentTaskRequest, context: dict = Depends(get_request_context)):
    if not supervisor_instance:
        raise HTTPException(status_code=503, detail="Supervisor Agent is offline.")
    try:
        user_id = context.get("user_id", "system")
        dept = context.get("department", "General")
        result = await supervisor_instance.run_task(req.task, user_id, dept, "TN")
        
        if result.status == "complete":
            return {
                "task_id": result.task_id or "new",
                "status": "complete",
                "answer": result.answer,
                "artifacts": result.artifacts,
                "steps_taken": result.steps_taken,
                "agents_used": result.agents_used
            }
        elif result.status == "awaiting_approval":
            return {
                "task_id": result.task_id,
                "status": "awaiting_approval",
                "pending_action": result.pending_action,
                "completed_so_far": result.completed_so_far,
                "message": "Please review and approve"
            }
    except Exception as e:
        logger.error(f"Agent task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent/task/{task_id}")
async def get_agent_task(task_id: str, context: dict = Depends(get_request_context)):
    return {"task_id": task_id, "status": "unknown"}

@app.post("/agent/task/{task_id}/approve")
async def approve_agent_task(task_id: str, req: AgentApproveRequest, context: dict = Depends(get_request_context)):
    try:
        result = await supervisor_instance.resume_after_approval(task_id, req.approved, req.edited_parameters)
        return {
            "task_id": task_id,
            "status": result.status,
            "answer": result.answer,
            "artifacts": result.artifacts,
            "steps_taken": result.steps_taken,
            "agents_used": result.agents_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
