import os
import uuid
import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from .specialist_agents import ResearchAgent, DocumentAgent, DataAgent, CommsAgent, CodeAgent, LawAgent, FinanceAgent

log = logging.getLogger("SupervisorAgent")

HUMAN_APPROVAL_REQUIRED = os.getenv("HUMAN_APPROVAL_REQUIRED", "true").lower() == "true"

@dataclass
class TaskResult:
    status: str
    answer: str = None
    pending_action: Any = None
    completed_so_far: dict = None
    plan: list = None
    task_id: str = None
    artifacts: list = None
    steps_taken: int = 0
    agents_used: list = None

class SupervisorAgent:
    def __init__(self):
        self.agents = {
            "research_agent": ResearchAgent(),
            "document_agent": DocumentAgent(),
            "data_agent": DataAgent(),
            "comms_agent": CommsAgent(),
            "code_agent": CodeAgent(),
            "law_agent": LawAgent(),
            "finance_agent": FinanceAgent()
        }
        # In full version, initialize Redis short-term memory and Qdrant long-term memory
        self.agent_memory_prefix = "agent_memory_"

    def load_memory(self, task: str, user_id: str, org_unit: str) -> str:
        # Load long term memory context
        log.info(f"Loading long term memory for {user_id} in {org_unit}")
        return "No relevant past context found."

    def save_memory(self, task: str, result: str, user_id: str, org_unit: str):
        log.info(f"Saving long term memory for {user_id} in {org_unit}")
        pass

    async def plan(self, task: str, past_context: str) -> List[Dict[str, Any]]:
        # Mocking LLM planning logic
        log.info(f"Planning task: {task[:50]}")
        # In a real environment, this calls LLaMA to break down the task
        
        # We'll just assign it to a research_agent if we don't do real LLM call here
        plan = [
            {"order": 1, "agent": "research_agent", "sub_task": f"Research: {task}", "depends_on": []}
        ]
        
        if "draft" in task.lower() or "report" in task.lower() or "email" in task.lower():
            plan.append({"order": 2, "agent": "document_agent", "sub_task": "Draft requested document", "depends_on": ["research_agent_1"]})
            
        return plan

    async def synthesise(self, task: str, results: dict) -> str:
        log.info("Synthesising final results from agent outputs")
        synth = "Task completed successfully.\n\nSummary of actions:\n"
        for key, res in results.items():
            synth += f"- {key}: {res}\n"
        return synth

    def collect_artifacts(self, results: dict) -> list:
        # Scan results for file paths
        artifacts = []
        for v in results.values():
            if isinstance(v, str) and (v.endswith(".pdf") or v.endswith(".png") or v.endswith(".docx")):
                artifacts.append({"path": v, "type": "file"})
        return artifacts

    async def run_task(self, task: str, user_id: str, org_unit: str, state_code: str) -> TaskResult:
        log.info(f"Supervisor started task for {user_id}")
        past_context = self.load_memory(task, user_id, org_unit)
        plan = await self.plan(task, past_context)
        
        results = {}
        for step in plan:
            agent_name = step["agent"]
            if agent_name not in self.agents:
                log.warning(f"Unknown agent: {agent_name}")
                continue
                
            agent = self.agents[agent_name]
            context = {
                "org_unit": org_unit, 
                "state_code": state_code,
                "prior_results": {k: results[k] for k in step.get("depends_on", []) if k in results}
            }
            
            agent_result = await agent.run(step["sub_task"], context)
            
            if agent_result.status == "needs_approval":
                task_id = str(uuid.uuid4())
                return TaskResult(
                    status="awaiting_approval",
                    pending_action=agent_result.pending_tool,
                    completed_so_far=results,
                    plan=plan,
                    task_id=task_id
                )
                
            results[f"{agent_name}_{step['order']}"] = agent_result.output
            
        final_answer = await self.synthesise(task, results)
        self.save_memory(task, final_answer, user_id, org_unit)
        
        return TaskResult(
            status="complete",
            answer=final_answer,
            artifacts=self.collect_artifacts(results),
            steps_taken=len(plan),
            agents_used=list({s["agent"] for s in plan})
        )

    async def resume_after_approval(self, task_id: str, approved: bool, edited_params: dict = None) -> TaskResult:
        # In reality, this loads state from Redis
        if not approved:
            return TaskResult(status="complete", answer="Action cancelled by user.", steps_taken=0)
            
        # Mock resume logic for now
        log.info(f"Resuming task {task_id} after approval")
        return TaskResult(
            status="complete",
            answer="Task resumed and completed successfully after approval.",
            artifacts=[],
            steps_taken=1,
            agents_used=["comms_agent"]
        )
