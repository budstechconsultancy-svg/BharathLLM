import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .tool_registry import get_tool

log = logging.getLogger("SpecialistAgents")

@dataclass
class AgentResult:
    status: str  # "complete", "needs_approval", "max_steps_reached", "error"
    output: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    pending_tool: Optional[Any] = None

class BaseSpecialistAgent:
    def __init__(self, name: str, system_prompt: str, available_tools: List[str], max_steps: int):
        self.name = name
        self.system_prompt = system_prompt
        self.available_tools = [get_tool(t) for t in available_tools if get_tool(t)]
        self.max_steps = max_steps

    async def run(self, task: str, context: dict) -> AgentResult:
        log.info(f"[{self.name}] Starting task: {task[:50]}...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Task: {task}\nContext: {context}"}
        ]
        
        # In a full implementation, this uses self.llm.generate()
        # Mocking the ReAct loop for architecture scaffolding
        
        for step in range(self.max_steps):
            # 1. LLM Generation (Mocked)
            # response = await llm.generate(messages, tools=self.available_tools)
            
            # For demonstration, we simply complete the task on step 1 unless it requires approval
            # Let's pretend the LLM calls the first available tool.
            if not self.available_tools:
                return AgentResult(status="error", output="No tools configured", messages=messages)
                
            mock_tool = self.available_tools[0]
            
            if mock_tool.requires_approval:
                log.info(f"[{self.name}] Tool {mock_tool.name} requires human approval. Pausing.")
                # We would normally return the actual pending tool call schema here
                return AgentResult(
                    status="needs_approval",
                    pending_tool={"name": mock_tool.name, "description": mock_tool.description, "parameters": {}},
                    messages=messages
                )
            
            # 2. Execute tool
            try:
                # Provide empty dict to satisfy mock params
                result = await mock_tool.execute() if mock_tool.name == "rag_search" else f"Mock result for {mock_tool.name}"
            except Exception as e:
                result = f"Error executing tool: {e}"
                
            messages.append({"role": "tool", "content": str(result)})
            
            # 3. Final generation
            final_output = f"[{self.name}] Task completed using {mock_tool.name}. Result: {str(result)[:50]}..."
            messages.append({"role": "assistant", "content": final_output})
            
            return AgentResult(status="complete", output=final_output, messages=messages)

        return AgentResult(status="max_steps_reached", messages=messages)

# --- Define the 5 Specialist Agents ---

class ResearchAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="research_agent",
            system_prompt=(
                "You are a government research specialist. Your job is to find "
                "accurate, cited information from government documents, websites, "
                "and databases. When you use rag_search, always include the "
                "department name. When you use web_search, prefer *.gov.in sites. "
                "Always translate if the source is in a different language than "
                "the user requested. Cite every source you use."
            ),
            available_tools=["rag_search", "web_search", "translate"],
            max_steps=8
        )

class DocumentAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="document_agent",
            system_prompt=(
                "You are a senior government document drafter with 20 years of "
                "experience writing G.O.s, circulars, proceedings, and official "
                "letters. Follow standard Government of India / State Government "
                "format exactly. Use formal language. Include all required sections. "
                "Always include the department name, ref number format, and "
                "By Order signature block. For Tamil Nadu: use both Tamil and "
                "English where appropriate."
            ),
            available_tools=["draft_document", "fill_form", "generate_report", "translate"],
            max_steps=6
        )

class DataAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="data_agent",
            system_prompt=(
                "You are a government data analyst. Query live databases, "
                "analyse spreadsheets, and produce accurate statistics. "
                "Always verify figures before reporting. When coverage or "
                "utilisation is below threshold, flag it explicitly. "
                "Generate charts to accompany tables when presenting district-wise data."
            ),
            available_tools=["sql_query", "analyse_excel", "generate_chart", "execute_python"],
            max_steps=8
        )

class CommsAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="comms_agent",
            system_prompt=(
                "You are a government communications officer. Draft clear, formal "
                "official communications. Always draft before sending — use draft_email "
                "first, then present it for approval, then use send_email. "
                "Match the language to the recipient's known preference. "
                "CC the appropriate senior officer for all communications above "
                "district level."
            ),
            available_tools=["draft_email", "send_email", "send_sms", "translate"],
            max_steps=5
        )

class CodeAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="code_agent",
            system_prompt=(
                "You are a government technology specialist. Write clean, safe Python "
                "code to solve data problems. Always describe what your code does before "
                "executing it. Never write code that modifies databases directly — "
                "use the sql_query tool for read queries. For govt API calls, use the "
                "call_govt_api tool with the correct api_name. Your code runs in an "
                "isolated sandbox with pandas, numpy, matplotlib, scipy available."
            ),
            available_tools=["execute_python", "generate_chart", "call_govt_api", "scrape_portal"],
            max_steps=8
        )

class LawAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="law_agent",
            system_prompt=(
                "You are the BharatLLM Legal Specialist Agent. "
                "Your primary role is to interpret, analyze, and draft legal documents, acts, rules, and government orders (G.O.s) for the Government of India and State Governments.\n\n"
                "GUIDELINES:\n"
                "1. Always cite specific Acts, Sections, and Rules when providing legal advice.\n"
                "2. Adhere strictly to the Constitution of India and established jurisprudence.\n"
                "3. If an order or rule is ambiguous, highlight the ambiguity and recommend consulting the Law Secretary or Advocate General.\n"
                "4. Maintain a formal, objective, and precise tone appropriate for government legal proceedings.\n"
                "5. Do NOT hallucinate legal precedents. If you are unsure, state that further legal research is required."
            ),
            available_tools=["rag_search", "web_search"],
            max_steps=6
        )

class FinanceAgent(BaseSpecialistAgent):
    def __init__(self):
        super().__init__(
            name="finance_agent",
            system_prompt=(
                "You are the BharatLLM Finance Specialist Agent. "
                "Your primary role is to handle financial analysis, budget allocations, auditing rules, and expenditure approvals for government departments.\n\n"
                "GUIDELINES:\n"
                "1. Always adhere to the General Financial Rules (GFR) and state-specific financial codes.\n"
                "2. When analyzing budgets, double-check all calculations for accuracy.\n"
                "3. Identify potential audit objections or deviations from standard procurement processes (e.g., GeM portal rules).\n"
                "4. Highlight any cost-overruns or unauthorized expenditures clearly.\n"
                "5. Provide data in clear, tabulated formats whenever possible.\n\n"
                "Never approve or recommend overriding a financial block without explicit manual approval from the Finance Secretary or authorized drawing and disbursing officer (DDO)."
            ),
            available_tools=["sql_query", "analyse_excel", "generate_chart"],
            max_steps=8
        )
