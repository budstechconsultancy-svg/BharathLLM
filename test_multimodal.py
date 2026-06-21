import os
import io
os.environ["DATABASE_URL"] = "sqlite:///./test_multimodal.db"
os.environ["MOCK_AI_MODELS"] = "True"

from fastapi.testclient import TestClient
from api.main import app, router_instance
from unittest.mock import MagicMock
import api.main

# Mock the QueryRouter
mock_router = MagicMock()
mock_router.route_and_query.return_value = {
    "answer": "This is a response generated from analyzing your multimodal input via QueryRouter.",
    "query_type": "MULTIMODAL_ROUTED",
    "sources": [],
    "sql_generated": False,
    "db_row_count": 0,
    "confidence": 0.99,
    "chunks_used": 0,
    "query_language": "en"
}
api.main.router_instance = mock_router

client = TestClient(app)

def create_mock_user():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api.db_models import Base
    from auth.auth_service import create_user
    
    engine = create_engine("sqlite:///./test_multimodal.db")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    from api.db_models import User
    if not db.query(User).filter(User.email == "multi@saas.com").first():
        create_user("multi@saas.com", "password", "Multi User", "Multi Corp", db)
    db.close()

def run_tests():
    create_mock_user()
    
    # 1. Login
    login_res = client.post("/auth/login", json={"employee_id_or_email": "multi@saas.com", "password": "password"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test Multimodal Endpoint with just Audio
    print("Testing Audio Query...")
    audio_bytes = b"fake_audio_content"
    res = client.post("/multimodal/query", headers=headers, files={"audio": ("test.webm", io.BytesIO(audio_bytes), "audio/webm")})
    
    if res.status_code == 200:
        data = res.json()
        print("Success! Response:", data["answer"])
        print("Unified Query generated:", data["unified_query"])
        print("Audio TTS generated:", "Yes" if "audio_answer_base64" in data else "No")
    else:
        print("Failed:", res.status_code, res.text)
        
    # 3. Test with Audio + Image + Text
    print("\nTesting Full Multimodal Query...")
    files = {
        "audio": ("test.webm", io.BytesIO(b"fake_audio"), "audio/webm"),
        "image": ("test.png", io.BytesIO(b"fake_image"), "image/png"),
    }
    data_payload = {"text": "What is the relation between this image and voice?"}
    
    res = client.post("/multimodal/query", headers=headers, files=files, data=data_payload)
    if res.status_code == 200:
        data = res.json()
        print("Success! Unified Query generated:\n", data["unified_query"])
    else:
        print("Failed:", res.status_code, res.text)

if __name__ == "__main__":
    if os.path.exists("./test_multimodal.db"):
        try: os.remove("./test_multimodal.db")
        except: pass
    run_tests()
