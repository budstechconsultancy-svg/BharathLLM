import os
import sys
from pathlib import Path
# Add parent directory to path to enable package resolution
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.db_models import User, Base
from auth.auth_service import hash_password

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/bharatllm")
ADMIN_MASTER_KEY = os.getenv("ADMIN_MASTER_KEY", "tn_master_super_admin_secret_key_pass_2026")

def main():
    print("Seeding initial Super Admin...")
    engine = create_engine(DATABASE_URL)
    
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if any admin already exists
        exists = db.query(User).filter(User.role == "super_admin").first()
        if exists:
            print(f"Super Admin already exists: {exists.employee_id}. Seeding skipped.")
            return
            
        hashed_pwd = hash_password(ADMIN_MASTER_KEY)
        
        super_admin = User(
            employee_id="ADM001",
            email="admin@llm.tn.gov.in",
            hashed_password=hashed_pwd,
            full_name="TN Master Super Admin",
            department="IT",
            role="super_admin",
            is_active=1
        )
        
        db.add(super_admin)
        db.commit()
        
        print("\nSeed completed successfully ✓")
        print("Master Credentials:")
        print(f"  Employee ID: {super_admin.employee_id}")
        print("  Password   : [ADMIN_MASTER_KEY from .env]")
        print("  Email      : admin@llm.tn.gov.in")
    except Exception as e:
        print(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
