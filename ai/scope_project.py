from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

class RouterDecision(BaseModel):
    is_actionable: bool = Field(description="True if input has both a Technical Medium and a Core Intent.")
    clarification_question: Optional[str] = Field(description="If not actionable, ask ONE short question to get the missing medium or intent.",default=None)
    tier: Optional[Literal["Tier 1", "Tier 2", "Tier 3"]] = Field(description="Tier 1: Simple/Fast, Tier 2: Medium web/app, Tier 3: Complex AI/Enterprise.",default=None,)

class BudgetRange(BaseModel):
    min: int
    max: int

class ProjectScope(BaseModel):
    reasoning_for_tier: str = Field(description="Chain-of-thought explaining why this timeline and budget fit the requested tier.")
    title: str = Field(description="Professional project title.")
    description: str = Field(description="Structured project brief.")
    deliverables: List[str] = Field(description="3-5 clear milestones.")
    timeline_weeks: int
    budget_range: BudgetRange
    required_skills: List[str] = Field(description="Extracted technical skills needed.")



def check_vagueness(client_input: str,structured_router) -> RouterDecision:
    prompt = PromptTemplate.from_template("""
    You are an intake classifier for a freelance marketplace.
    Determine if the client's request is actionable. It MUST contain:
    1. A Technical Medium (e.g., website, app, script, design)
    2. A Core Intent (e.g., sell products, track data)
    
    If actionable, assign a complexity Tier (1, 2, or 3).
    If missing the medium or intent, set is_actionable to false and ask exactly ONE short clarification question.
    
    Client Input: {input}
    """)
    
    try:
        return structured_router.invoke(prompt.format(input=client_input))
    except Exception as e:
        print(f"Router Failed: {e}")
        return RouterDecision(is_actionable=False, clarification_question="Could you provide more details about what you want to build?")

def generate_project_scope(client_input: str, tier: str,structured_generator) -> ProjectScope:
    prompt = PromptTemplate.from_template("""
    You are an expert technical project manager. Transform the client's idea into a structured project scope.
    
    Client Input: {input}
    Assigned Complexity: {tier}
    
    Generate realistic deliverables, a timeline in weeks, a realistic USD budget range, and extract the necessary technical skills.
    """)
    
    try:
        return structured_generator.invoke(prompt.format(input=client_input, tier=tier))
    except Exception as e:
        print(f"Generator Failed: {e}")
        return ProjectScope(
            reasoning_for_tier="Error parsing.", title="Draft Project", description=client_input,
            deliverables=[], timeline_weeks=1, budget_range=BudgetRange(min=0, max=0), required_skills=[]
        )


def scope_project_pipeline(client_input: str,generator_llm,VALID_SKILLS_DB) -> Dict[str, Any]:
    # 1a: Fast Vagueness Check
    router_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0) # change later to light weight
    structured_router = router_llm.with_structured_output(RouterDecision)
    structured_generator = generator_llm.with_structured_output(ProjectScope)
    router_decision = check_vagueness(client_input,structured_router)

    if not router_decision.is_actionable:
        return {
            "status": "needs_clarification",
            "prompt_to_user": router_decision.clarification_question
        }
        
    # 2: Generate Scope
    scope = generate_project_scope(client_input, router_decision.tier,structured_generator)
    
    # 3: Backend Verification
    verified_skills = [
        skill for skill in scope.required_skills 
        if any(db_skill.lower() == skill.lower() for db_skill in VALID_SKILLS_DB)
    ]
    payload = scope.model_dump()
    payload["required_skills"] = verified_skills
    
    return {
        "status": "draft_ready",
        "tier_assigned": router_decision.tier,
        "draft_data": payload
    }