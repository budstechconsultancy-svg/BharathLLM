import os
import re
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logger
logger = logging.getLogger("SQLEngine")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/bharatllm")

# Structured database schema descriptions cache
SCHEMA_DESCRIPTION = """
Table: scheme_enrollments
Columns:
  - id (INTEGER) - Primary key
  - scheme_name (VARCHAR(255)) - Name of the government scheme
  - beneficiary_name (VARCHAR(255)) - Name of enrolled beneficiary
  - district (VARCHAR(100)) - District location
  - block (VARCHAR(100)) - Block location
  - year (INTEGER) - Calendar enrollment year
  - enrollment_date (DATE) - Enrollment date
  - status (VARCHAR(50)) - Status (e.g. Active, Pending)
  - department (VARCHAR(100)) - Sponsoring department name
  - created_at (TIMESTAMP) - Ingestion timestamp

Table: budget_allocations
Columns:
  - id (INTEGER) - Primary key
  - department (VARCHAR(100)) - Owner department name
  - scheme_name (VARCHAR(255)) - Associated scheme name
  - financial_year (VARCHAR(20)) - Financial year span (e.g. 2024-25)
  - allocated_amount (NUMERIC) - Budget allocated
  - released_amount (NUMERIC) - Budget released
  - spent_amount (NUMERIC) - Budget utilized
  - balance (NUMERIC) - Budget balance amount
  - as_of_date (DATE) - Allocation reporting date

Table: employees
Columns:
  - id (INTEGER) - Primary key
  - employee_id (VARCHAR(100)) - Unique ID identifier
  - name (VARCHAR(255)) - Staff employee name
  - designation (VARCHAR(100)) - Job designation title
  - grade (VARCHAR(20)) - Staff grade level (e.g. Grade 4)
  - department (VARCHAR(100)) - Staff department
  - district (VARCHAR(100)) - Working district
  - posting_date (DATE) - Posting appointment date
  - status (VARCHAR(50)) - Status (Active, Retired, Transferred)

Table: hospitals
Columns:
  - id (INTEGER) - Primary key
  - name (VARCHAR(255)) - Hospital facility name
  - district (VARCHAR(100)) - District location
  - block (VARCHAR(100)) - Block location
  - type (VARCHAR(50)) - Facility type (PHC, CHC, GH, TH)
  - bed_count (INTEGER) - Facility total beds
  - doctor_count (INTEGER) - Doctor count
  - nurse_count (INTEGER) - Nurse count
  - department (VARCHAR(100)) - Managing department

Table: schools
Columns:
  - id (INTEGER) - Primary key
  - name (VARCHAR(255)) - School name
  - district (VARCHAR(100)) - District location
  - block (VARCHAR(100)) - Block location
  - type (VARCHAR(100)) - School category type
  - student_count (INTEGER) - Student count
  - teacher_count (INTEGER) - Teacher count
  - medium (VARCHAR(50)) - Instruction language medium (Tamil, English)
  - department (VARCHAR(100)) - Sponsoring department

Table: land_records
Columns:
  - id (INTEGER) - Primary key
  - survey_no (VARCHAR(100)) - Survey block number
  - district (VARCHAR(100)) - District location
  - taluk (VARCHAR(100)) - Taluk location
  - village (VARCHAR(100)) - Village location
  - owner_name (VARCHAR(255)) - Landowner register name
  - patta_no (VARCHAR(100)) - Patta register index number
  - area_acres (NUMERIC) - Total land acreage
  - land_type (VARCHAR(100)) - Land type
  - last_updated (DATE) - Entry date update
"""

class SQLEngine:
    def __init__(self, llm_engine=None):
        # llm_engine references the loaded RAGEngine instance (re-uses existing loaded LLM)
        self.llm_engine = llm_engine
        
        # 1. Establish Read-only DB connection Engine
        try:
            self.engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                connect_args={"options": "-c default_transaction_read_only=on"} # enforce read-only at session level
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("SQLEngine read-only connection initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            self.engine = None
            self.SessionLocal = None
            
        self.schema_description = SCHEMA_DESCRIPTION

from pipeline.language_registry import normalise_numerals

SCHEMA_MAP = {
    "beneficiaries": ("scheme_enrollments", "COUNT(*)", "status='active'"),
    "enrolled": ("scheme_enrollments", "COUNT(*)", None),
    "budget": ("budget_allocations", "SUM(allocated_amount)", None),
    "expenditure": ("budget_allocations", "SUM(spent_amount)", None),
    "spent": ("budget_allocations", "SUM(spent_amount)", None),
    "balance": ("budget_allocations", "SUM(balance)", None),
    "employees": ("employees", "COUNT(*)", "status='active'"),
    "staff": ("employees", "COUNT(*)", "status='active'"),
    "hospitals": ("hospitals", "COUNT(*)", None),
    "beds": ("hospitals", "SUM(bed_count)", None),
    "doctors": ("hospitals", "SUM(doctor_count)", None),
    "schools": ("schools", "COUNT(*)", None),
    "students": ("schools", "SUM(student_count)", None),
    "teachers": ("schools", "SUM(teacher_count)", None),
}

QUERY_TEMPLATES = {
    "list_by_dept":
      "SELECT * FROM {table} WHERE department='{dept}' LIMIT {limit}",
    "count_by_district":
      "SELECT district, COUNT(*) as count FROM {table} WHERE department='{dept}' GROUP BY district ORDER BY count DESC LIMIT 20",
    "sum_by_year":
      "SELECT year, SUM({amount_col}) as total FROM {table} WHERE department='{dept}' GROUP BY year ORDER BY year DESC LIMIT 5",
}

class SQLEngine:
    def __init__(self, llm_engine=None):
        self.llm_engine = llm_engine
        
        try:
            self.engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                connect_args={"options": "-c default_transaction_read_only=on"}
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("SQLEngine read-only connection initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            self.engine = None
            self.SessionLocal = None
            
        self.schema_description = SCHEMA_DESCRIPTION

    def generate_sql_tier1(self, question: str, department: str) -> str | None:
        question_lower = question.lower()
        matched = []
        for keyword, (table, agg, extra_where) in SCHEMA_MAP.items():
            if keyword in question_lower:
                matched.append((table, agg, extra_where))
        if not matched:
            return None

        table, agg, extra_where = matched[0]
        where_clauses = []
        
        # Check if department column exists in the target table (assume it does for standard tables except maybe some general ones)
        if table in ["scheme_enrollments", "budget_allocations", "employees", "hospitals", "schools"]:
            where_clauses.append(f"department='{department}'")
            
        if extra_where:
            where_clauses.append(extra_where)

        year_match = re.search(r'\b(20\d{2})\b', normalise_numerals(question))
        if year_match:
            # check which table has year
            if table == "scheme_enrollments":
                where_clauses.append(f"year={year_match.group(1)}")
            elif table == "budget_allocations":
                where_clauses.append(f"financial_year LIKE '%{year_match.group(1)}%'")

        district_match = re.search(r'\bin\s+([A-Za-z\u0900-\u0D7F]+)\b', question, re.IGNORECASE)
        if district_match:
            where_clauses.append(f"district='{district_match.group(1).title()}'")

        where = " AND ".join(where_clauses)
        where_str = f" WHERE {where}" if where_clauses else ""
        sql = f"SELECT {agg} as result FROM {table}{where_str} LIMIT 100"
        return sql

    def generate_sql_tier2(self, question: str, department: str) -> str | None:
        question_lower = question.lower()
        
        # Detect table
        table = None
        if any(w in question_lower for w in ["enroll", "beneficiar"]):
            table = "scheme_enrollments"
        elif any(w in question_lower for w in ["budget", "spent", "expenditure", "allocat"]):
            table = "budget_allocations"
        elif any(w in question_lower for w in ["employee", "staff"]):
            table = "employees"
        elif any(w in question_lower for w in ["hospital", "bed", "doctor"]):
            table = "hospitals"
        elif any(w in question_lower for w in ["school", "student", "teacher"]):
            table = "schools"
        elif any(w in question_lower for w in ["land", "patta", "survey"]):
            table = "land_records"
            
        if not table:
            return None

        if any(w in question_lower for w in ["list", "show all", "get all"]):
            return QUERY_TEMPLATES["list_by_dept"].format(table=table, dept=department, limit=100)
        elif any(w in question_lower for w in ["by district", "district-wise", "districtwise"]):
            return QUERY_TEMPLATES["count_by_district"].format(table=table, dept=department)
        elif any(w in question_lower for w in ["by year", "year-wise", "financial year"]):
            amount_col = "allocated_amount"
            if "spent" in question_lower or "expenditure" in question_lower:
                amount_col = "spent_amount"
            # Note: year column varies
            year_col = "year" if table == "scheme_enrollments" else "financial_year"
            return f"SELECT {year_col}, SUM({amount_col}) as total FROM {table} WHERE department='{department}' GROUP BY {year_col} ORDER BY {year_col} DESC LIMIT 5"
            
        return f"SELECT * FROM {table} WHERE department='{department}' LIMIT 100"

    def generate_sql(self, question: str, department: str) -> str:
        # Tier 1: Keyword-to-column mapping
        sql = self.generate_sql_tier1(question, department)
        if sql:
            return sql
            
        # Tier 2: Template fill
        sql = self.generate_sql_tier2(question, department)
        if sql:
            return sql
            
        # Tier 3: Fallback (empty string to trigger error response in query method)
        return ""

    def validate_sql(self, sql: str) -> str | None:
        if not sql:
            return None
            
        sql_upper = sql.upper().strip()
        
        # 1. Reject mutating keywords
        mutation_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
        for kw in mutation_keywords:
            # Match boundary word to prevent false positive (e.g. matching "altered" or "created_at")
            if re.search(rf"\b{kw}\b", sql_upper):
                logger.error(f"SQL Validation Error: Detected banned mutating keyword: {kw}")
                return None
                
        # 2. Reject if does not start with SELECT
        if not sql_upper.startswith("SELECT"):
            logger.error("SQL Validation Error: Query must start with SELECT.")
            return None
            
        # 3. Force LIMIT clause addition
        if "LIMIT" not in sql_upper:
            # Auto-add LIMIT 100 before execution
            sql = sql.rstrip("; ") + " LIMIT 100"
            
        return sql

    def execute_sql(self, sql: str) -> dict:
        if not self.SessionLocal:
            return {"error": "Database session not initialized", "rows": [], "column_names": []}
            
        sanitized_sql = self.validate_sql(sql)
        if not sanitized_sql:
            return {"error": "SQL Query failed verification filters", "rows": [], "column_names": []}
            
        session = self.SessionLocal()
        try:
            result = session.execute(text(sanitized_sql))
            rows = [dict(row._mapping) for row in result]
            column_names = list(result.keys())
            return {
                "error": None,
                "rows": rows,
                "column_names": column_names,
                "row_count": len(rows)
            }
        except Exception as e:
            logger.error(f"SQL Execution Error: {e}")
            return {
                "error": str(e),
                "rows": [],
                "column_names": [],
                "row_count": 0
            }
        finally:
            session.close()

    def format_results(self, question: str, rows: list, column_names: list) -> str:
        row_count = len(rows)
        if row_count == 0:
            return "No records found in the database for this query."
            
        # If single row and single column output, return direct string
        if row_count == 1 and len(column_names) == 1:
            val = list(rows[0].values())[0]
            return f"Answer: {val}"
            
        # For <= 10 rows, construct textual markdown layout table
        if row_count <= 10:
            header = " | ".join(column_names)
            separator = " | ".join(["---"] * len(column_names))
            table_lines = [header, separator]
            for row in rows:
                row_vals = [str(row.get(col, "")) for col in column_names]
                table_lines.append(" | ".join(row_vals))
            return "\n".join(table_lines)
            
        # For > 10 rows, summarize structure
        summary = f"Found {row_count} records. Showing first 10:\n"
        header = " | ".join(column_names)
        separator = " | ".join(["---"] * len(column_names))
        table_lines = [summary, header, separator]
        for row in rows[:10]:
            row_vals = [str(row.get(col, "")) for col in column_names]
            table_lines.append(" | ".join(row_vals))
            
        return "\n".join(table_lines)

    def query(self, question: str, department: str) -> dict:
        generated_sql = self.generate_sql(question, department)
        if not generated_sql:
            return {
                "sql_generated": None,
                "rows": [],
                "formatted_result": "Failed to translate question to SQL.",
                "error": "Translation failed",
                "row_count": 0
            }
            
        res = self.execute_sql(generated_sql)
        formatted = self.format_results(question, res["rows"], res["column_names"])
        
        return {
            "sql_generated": generated_sql,
            "rows": res["rows"],
            "formatted_result": formatted,
            "error": res["error"],
            "row_count": res.get("row_count", 0)
        }

if __name__ == "__main__":
    print("SQLEngine script syntax check passed.")
