from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .db_models import Base
import os

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():  # FastAPI dependency
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
