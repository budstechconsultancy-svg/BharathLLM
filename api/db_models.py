from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey, Text, Numeric, Date, JSON
from sqlalchemy.orm import DeclarativeBase
import uuid
import datetime

# Cross-database UUID helper — uses String(36) so it works with SQLite (dev) and PostgreSQL (prod)
def new_uuid():
    return str(uuid.uuid4())

UUID_TYPE = String(36)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    employee_id = Column(String(50), unique=True, nullable=True) # Nullable for SaaS users
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)  # null for super_admin
    ministry = Column(String(100), nullable=True)    # for Central Govt
    state_code = Column(String(5), nullable=True)    # e.g. "TN", "MH"
    role = Column(String(20), nullable=False)
    preferred_language = Column(String(10), default="en")
    organization_name = Column(String(255), nullable=True)
    subscription_tier = Column(String(50), default="free")
    jurisdiction_district = Column(String(100), nullable=True) # Fix F-3: Hierarchical Access
    api_quota_limit = Column(Integer, default=100)
    api_quota_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    key_hash = Column(String(64), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    created_by_user_id = Column(UUID_TYPE, ForeignKey("users.id"))
    rate_limit_per_min = Column(Integer, default=100)
    allowed_departments = Column(JSON, nullable=True)  # Fix 2.2: e.g. ["hr", "finance"] or null for all
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    user_id = Column(UUID_TYPE, ForeignKey("users.id"))
    token_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)

class SchemeEnrollment(Base):
    __tablename__ = "scheme_enrollments"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    scheme_name = Column(String(255), nullable=False)
    beneficiary_name = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    block = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    year = Column(Integer, nullable=True)
    enrollment_date = Column(Date, nullable=True)
    status = Column(String(50), default="active")
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

class BudgetAllocation(Base):
    __tablename__ = "budget_allocations"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    scheme_name = Column(String(255), nullable=True)
    financial_year = Column(String(10), nullable=False)
    allocated_amount = Column(Numeric(15,2), nullable=True)
    released_amount = Column(Numeric(15,2), nullable=True)
    spent_amount = Column(Numeric(15,2), nullable=True)
    balance = Column(Numeric(15,2), nullable=True)
    as_of_date = Column(Date, nullable=True)

class Employee(Base):
    __tablename__ = "employees"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    employee_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    designation = Column(String(255), nullable=True)
    grade = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    district = Column(String(100), nullable=True)
    posting_date = Column(Date, nullable=True)
    status = Column(String(30), default="active")

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    district = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    block = Column(String(100), nullable=True)
    type = Column(String(20), nullable=True)  # PHC/CHC/GH/TH/AIIMS
    bed_count = Column(Integer, default=0)
    doctor_count = Column(Integer, default=0)
    nurse_count = Column(Integer, default=0)
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)

class School(Base):
    __tablename__ = "schools"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    district = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    block = Column(String(100), nullable=True)
    type = Column(String(50), nullable=True)
    student_count = Column(Integer, default=0)
    teacher_count = Column(Integer, default=0)
    medium = Column(String(100), nullable=True)   # language of instruction
    department = Column(String(100), nullable=True)
    ministry = Column(String(100), nullable=True)

class LandRecord(Base):
    __tablename__ = "land_records"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    survey_no = Column(String(50), nullable=True)
    district = Column(String(100), nullable=True)
    taluk = Column(String(100), nullable=True)
    village = Column(String(100), nullable=True)
    state_code = Column(String(5), nullable=True)
    owner_name = Column(String(255), nullable=True)
    patta_no = Column(String(50), nullable=True)
    area_acres = Column(Float, nullable=True)
    land_type = Column(String(100), nullable=True)
    last_updated = Column(Date, nullable=True)

# Fix F-1: Audit log for RTI compliance
class QueryAuditLog(Base):
    __tablename__ = "query_audit_logs"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    query_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=True)
    answer_text = Column(Text, nullable=False)
    sources_cited = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Fix F-5: Human in the loop feedback
class QueryFeedback(Base):
    __tablename__ = "query_feedback"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    query_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# UPSC Prelims Quiz Models
class MCQQuiz(Base):
    __tablename__ = "upsc_mcq_quizzes"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    topic = Column(String(255), nullable=False)
    num_questions = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class MCQQuestion(Base):
    __tablename__ = "upsc_mcq_questions"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    quiz_id = Column(UUID_TYPE, nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(String(500), nullable=False)
    option_b = Column(String(500), nullable=False)
    option_c = Column(String(500), nullable=False)
    option_d = Column(String(500), nullable=False)
    correct_option = Column(String(1), nullable=False) # A, B, C, or D
    explanation = Column(Text, nullable=True)

class MCQAttempt(Base):
    __tablename__ = "upsc_mcq_attempts"
    id = Column(UUID_TYPE, primary_key=True, default=new_uuid)
    quiz_id = Column(UUID_TYPE, nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    total_questions = Column(Integer, nullable=False)
    attempted_at = Column(DateTime, default=datetime.datetime.utcnow)
