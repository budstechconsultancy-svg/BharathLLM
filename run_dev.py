"""
run_dev.py -- BharatLLM v3.1 -- Zero-dependency dev launcher
Runs the full app using:
  - SQLite instead of PostgreSQL (no install needed)
  - fakeredis instead of Redis (no install needed)
  - Qdrant skipped (RAG returns graceful fallback)
  - LLM model skipped (SQL engine works fully, RAG returns placeholder)

Usage:
    python run_dev.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
import sys
import subprocess
import importlib

# ── 1. Point DATABASE_URL at a local SQLite file ─────────────────────────────
DB_PATH = os.path.abspath("data/dev.sqlite3")
os.makedirs("data", exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["MOCK_AI_MODELS"] = "True"
os.environ.setdefault("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRY_HOURS", "8")
os.environ.setdefault("ADMIN_MASTER_KEY", "dev-admin-key")
os.environ.setdefault("DEPLOYMENT_MODE", "STATE_GOVT")
os.environ.setdefault("DEPLOYMENT_STATE", "TN")
os.environ.setdefault("PRIMARY_LANGUAGES", "ta,en,hi")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# ── 2. Patch redis to use fakeredis so rate-limiter / celery don't crash ──────
try:
    import fakeredis
    import redis as _redis_module

    _fake_server = fakeredis.FakeServer()

    class _PatchedRedis:
        """Drop-in fakeredis client that satisfies redis.Redis interface."""
        def __new__(cls, *args, **kwargs):
            return fakeredis.FakeRedis(server=_fake_server, decode_responses=kwargs.get("decode_responses", False))

        @staticmethod
        def from_url(url, **kwargs):
            return fakeredis.FakeRedis(server=_fake_server, decode_responses=kwargs.get("decode_responses", False))

    _redis_module.Redis = _PatchedRedis
    _redis_module.StrictRedis = _PatchedRedis
    sys.modules["redis"].Redis = _PatchedRedis
    sys.modules["redis"].StrictRedis = _PatchedRedis
    print("[DEV] fakeredis patched in — no Redis server required")
except Exception as e:
    print(f"[WARN] Could not patch fakeredis: {e}")

# ── 3. Create DB schema + seed admin user ─────────────────────────────────────
print(f"[DEV] Using SQLite database: {DB_PATH}")

sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False}
)

from api.db_models import Base, User
Base.metadata.create_all(bind=engine)
print("[DEV] Database schema created / verified")

# Seed admin user if not exists
from auth.auth_service import hash_password
Session = sessionmaker(bind=engine)
with Session() as session:
    existing = session.query(User).filter_by(employee_id="admin").first()
    if not existing:
        admin = User(
            employee_id="admin",
            email="admin@tn.gov.in",
            hashed_password=hash_password("Admin@1234"),
            full_name="System Administrator",
            role="super_admin",
            state_code="TN",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        print("[DEV] Admin user seeded  ->  employee_id: admin  |  password: Admin@1234")
    else:
        print("[DEV] Admin user already exists  ->  employee_id: admin  |  password: Admin@1234")

    existing_user = session.query(User).filter_by(employee_id="user").first()
    if not existing_user:
        standard_user = User(
            employee_id="user",
            email="user@tn.gov.in",
            hashed_password=hash_password("User@1234"),
            full_name="Standard User",
            role="user",
            state_code="TN",
            department="Health",
            is_active=True,
        )
        session.add(standard_user)
        session.commit()
        print("[DEV] Standard user seeded  ->  employee_id: user  |  password: User@1234")
    else:
        print("[DEV] Standard user already exists  ->  employee_id: user  |  password: User@1234")

# ── 4. Patch main.py DATABASE_URL before uvicorn imports it ──────────────────
import api.main as _main_mod
_main_mod.DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── 5. Start uvicorn ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  BharatLLM v3.1  --  Dev Server Starting")
print("="*60)
print(f"  API   ->  http://127.0.0.1:8000")
print(f"  Docs  ->  http://127.0.0.1:8000/docs")
print(f"  UI    ->  http://localhost:5173")
print(f"  DB    ->  SQLite ({DB_PATH})")
print(f"  Redis ->  fakeredis (in-memory)")
print("="*60 + "\n")

import multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,   # reload=True causes Windows multiprocessing issues outside __main__
        log_level="info",
    )
