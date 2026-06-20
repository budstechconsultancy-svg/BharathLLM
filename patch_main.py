import sys

with open('api/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports_to_add = """from workers.job_store import get_job, list_jobs
from agents.supervisor import SupervisorAgent
from api.multimodal_routes import router as multimodal_router
from api.whatsapp_webhook import router as whatsapp_router"""

content = content.replace("from workers.job_store import get_job, list_jobs", imports_to_add)

models_to_add = """    top_k: Optional[int] = 5
    override_department: Optional[str] = None

class AgentTaskRequest(BaseModel):
    task: str
    priority: Optional[str] = "normal"

class AgentApproveRequest(BaseModel):
    approved: bool
    edited_parameters: Optional[dict] = None"""

content = content.replace("    top_k: Optional[int] = 5\n    override_department: Optional[str] = None", models_to_add)

globals_to_add = """# Global state trackers
router_instance: Optional[QueryRouter] = None
supervisor_instance: Optional[SupervisorAgent] = None"""

content = content.replace("# Global state trackers\nrouter_instance: Optional[QueryRouter] = None", globals_to_add)

lifespan_to_add = """    # 2. Initialize ML Engines
    try:
        model_path = os.getenv("MODEL_NAME")
        router_instance = QueryRouter(model_path=model_path)
        supervisor_instance = SupervisorAgent()
        MODEL_LOADED.set(1)"""

content = content.replace("""    # 2. Instantiate QueryRouter
    try:
        router_instance = QueryRouter()""", lifespan_to_add)

routers_to_add = """app = FastAPI(
    title="BharatLLM Unified API",
    version="1.0.0",
    lifespan=lifespan
)

# Mount Routers
app.include_router(multimodal_router)
app.include_router(whatsapp_router)"""

content = content.replace("""app = FastAPI(
    title="BharatLLM Document Intelligence System API Gateway",
    version="1.0.0",
    lifespan=lifespan
)""", routers_to_add)

agent_endpoints = """# ----------------- AGENT ENDPOINTS -----------------

@app.post("/agent/task")
async def agent_task(req: AgentTaskRequest, context: dict = Depends(get_request_context)):
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
"""

if "def generate_scoped_api_key" in content:
    content = content + "\n\n" + agent_endpoints
else:
    print("WARNING: generate_scoped_api_key not found to append at EOF")

with open('api/main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("api/main.py successfully patched.")
