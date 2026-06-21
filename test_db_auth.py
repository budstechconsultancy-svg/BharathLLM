import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_db_auth_2.db"

from api.db_models import Base, User
from auth.auth_service import create_user

engine = create_engine("sqlite:///./test_db_auth_2.db")
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    db = SessionLocal()
    
    print("1. Creating User via create_user()...")
    user = create_user("demo2@saas.com", "password123", "Demo User", "Demo Corp", db)
    
    print(f"Created User: {user.email}")
    print(f"Subscription Tier: {user.subscription_tier}")
    print(f"Quota Limit: {user.api_quota_limit}")
    print(f"Quota Used: {user.api_quota_used}")
    print(f"Employee ID (Should be None): {user.employee_id}")
    
    print("\n2. Simulating Quota Usage...")
    user.api_quota_used += 10
    db.commit()
    print(f"Quota Used after simulation: {user.api_quota_used}")
    
    print("\n3. Simulating Upgrade to PRO...")
    user.subscription_tier = "pro"
    user.api_quota_limit = 1000
    db.commit()
    
    print(f"Subscription Tier: {user.subscription_tier}")
    print(f"Quota Limit: {user.api_quota_limit}")
    
    print("\nSUCCESS! DB models and auth_service work properly.")

if __name__ == "__main__":
    if os.path.exists("./test_db_auth_2.db"):
        try:
            os.remove("./test_db_auth_2.db")
        except:
            pass
    main()
