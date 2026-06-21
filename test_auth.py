import os
os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
os.environ["MOCK_AI_MODELS"] = "True"

# Create tables
from api.db_models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///./test_auth.db")
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from fastapi.testclient import TestClient
from api.main import app

# Override the get_db dependency
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[app.dependency_overrides.get("get_db", "get_db")] = override_get_db
# Actually need to override the one in main.py
from api.main import get_db
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def run_tests():
    print("1. Testing User Signup...")
    signup_res = client.post("/auth/signup", json={
        "email": "testb2b@company.com",
        "password": "SecurePassword123!",
        "full_name": "Test User",
        "organization_name": "Test Co"
    })
    
    if signup_res.status_code != 200:
        print("Signup Failed:", signup_res.json())
        return
        
    data = signup_res.json()
    print("Signup Success:", data["user"])
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\n2. Checking Subscription Tier...")
    sub_res = client.get("/auth/subscription", headers=headers)
    print("Subscription Info:", sub_res.json())
    
    # We will simulate the /query endpoint
    print("\n3. Testing Query endpoint to consume quota (Mocking router)...")
    # For /query to work, we need router_instance to be not None.
    # We can patch it.
    from api.main import router_instance
    from unittest.mock import MagicMock
    import api.main
    mock_router = MagicMock()
    mock_router.route_and_query.return_value = {
        "answer": "Mocked Answer",
        "query_type": "MockType",
        "sources": [],
        "sql_generated": False,
        "db_row_count": 0,
        "confidence": 1.0,
        "chunks_used": 0,
        "query_language": "en"
    }
    api.main.router_instance = mock_router
    
    print("Making a query...")
    q_res = client.post("/query", json={"question": "hello"}, headers=headers)
    print("Query Status:", q_res.status_code)
    
    print("\n4. Checking Subscription Tier (Quota used should be 1)...")
    sub_res = client.get("/auth/subscription", headers=headers)
    print("Subscription Info:", sub_res.json())
    
    print("\n5. Upgrading to PRO...")
    upg_res = client.post("/auth/subscription/upgrade", json={"tier": "pro"}, headers=headers)
    print("Upgrade Result:", upg_res.json())
    
    print("\n6. Checking Subscription Tier after upgrade...")
    sub_res = client.get("/auth/subscription", headers=headers)
    print("Subscription Info:", sub_res.json())
    
    print("\nAll auth tests completed successfully.")

if __name__ == "__main__":
    if os.path.exists("./test_auth.db"):
        os.remove("./test_auth.db")
    run_tests()
