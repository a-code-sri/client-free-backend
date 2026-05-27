import re
import json
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any
from langchain_core.prompts import PromptTemplate



def run_deterministic_checks(portfolio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scans the portfolio for structural flaws using hardcoded rules.
    Includes advanced cross-referencing for skill verification.
    """
    findings = {
        "profile_warnings": [],
        "orphaned_skills": [],
        "projects_needing_links": [],
        "projects_needing_visuals": [],
        "projects_lacking_impact": [],
        "formatting_warnings": []
    }

    bio = portfolio.get("bio", "")
    if len(bio) < 50:
        findings["profile_warnings"].append("Bio is too short (under 50 characters).")
        
    global_skills = set(portfolio.get("skills", []))
    if len(global_skills) < 3:
        findings["profile_warnings"].append("Too few skills listed. Recommend at least 3 to 5 core skills.")

    if not portfolio.get("work_experience"):
        findings["profile_warnings"].append("No work experience listed. Even freelance or informal client work should be added here.")

    all_project_tech = set()
    for proj in portfolio.get("projects", []):
        for tech in proj.get("tech_stack", []):
            all_project_tech.add(tech)

    for skill in global_skills:
        if skill not in all_project_tech:
            findings["orphaned_skills"].append(skill)

    impact_keywords = r'(\d+%|\d+x|reduced|increased|optimized|saved|scaled|users|revenue|faster|improved)'
    
    for proj in portfolio.get("projects", []):
        title = proj.get("title", "Untitled Project")
        desc = proj.get("description", "")
        
        # Check 1: Live Links
        if not proj.get("link"):
            findings["projects_needing_links"].append(title)
            
        # Check 2: Visuals/Thumbnails
        if not proj.get("images") or len(proj.get("images")) == 0:
            findings["projects_needing_visuals"].append(title)
            
        # Check 3: Description Depth
        if len(desc) < 100:
            findings["formatting_warnings"].append(f"'{title}': Description is too short. Explain the problem and your solution.")
            
        # Check 4: Wall of Text (Hard to read)
        if len(desc) > 400 and "\n" not in desc:
            findings["formatting_warnings"].append(f"'{title}': Description is a wall of text. Use line breaks or bullet points.")
            
        # Check 5: Impact Metrics (Regex)
        if not re.search(impact_keywords, desc.lower()):
            findings["projects_lacking_impact"].append(title)

    return findings

class FeedbackItem(BaseModel):
    category: str = Field(description="e.g., 'Bio', 'Project: E-Commerce'")
    issue: str = Field(description="The specific qualitative problem found.")
    suggestion: str = Field(description="Actionable advice to fix it.")

class RateEvaluation(BaseModel):
    is_appropriate: bool = Field(description="Whether the current rate aligns with the stated experience and skills.")
    analysis: str = Field(description="Brief explanation of why the rate is or isn't appropriate.")
    suggested_range: str = Field(description="e.g., '$40 - $60'")

class PortfolioCritique(BaseModel):
    overall_score: Literal["High", "Medium", "Low"] = Field(description="Overall portfolio quality score based on all aspects.")
    hourly_rate_evaluation: RateEvaluation
    qualitative_feedback: List[FeedbackItem]


def generate_llm_critique(portfolio: Dict[str, Any], deterministic_findings: Dict[str, Any],structured_llm) -> dict:
    """
    Uses LangChain's structured output with Pydantic to guarantee a perfect JSON payload.
    Evaluates qualitative feedback, hourly rate feasibility, and overall score.
    """
    prompt_template = PromptTemplate.from_template("""
    You are an expert technical recruiter auditing a freelancer's portfolio.

    Evaluate them against the "Top Earner Principles":
    1. Niche Authority: Does their bio position them as a specialist or a generalist? (Specialists command higher rates).
    2. Business Impact: Do their projects mention ROI, performance metrics, or scalable architecture, or do they just list basic tech stacks?
    3. Market Reality: Does their requested hourly rate match the complexity of the projects they've displayed?

    Freelancer Profile Data:
    {portfolio_data}

    Structural Flaws Caught by Backend:
    {backend_findings}
                                                   
    Your Tasks:
    1. Score the portfolio: Assign an overall_score of High, Medium, or Low based on the quality of experience and project descriptions.
    2. Evaluate the Hourly Rate: Look at their stated 'hourly_rate'. Compare it against their 'skills' and 'work_experience'. Is it too high for a junior? Too low for a senior architect? Provide an analysis and a suggested range.
    3. Qualitative Feedback: Provide 2-3 specific, actionable suggestions about their tone, alignment of skills to projects, or technical depth.
    """)
    
    prompt = prompt_template.format(
        portfolio_data=json.dumps(portfolio),
        backend_findings=json.dumps(deterministic_findings)
    )
    
    try:
        critique_obj = structured_llm.invoke(prompt)
        return critique_obj.model_dump()
        
    except Exception as e:
        print(f"LLM Critic Failed: {e}")
        return {
            "overall_score": "Low",
            "hourly_rate_evaluation": {
                "is_appropriate": False,
                "analysis": "Evaluation failed to process.",
                "suggested_range": "N/A"
            },
            "qualitative_feedback": []
        }
    
def review_portfolio(portfolio: Dict[str, Any],llm) -> Dict[str, Any]:
    """
    Orchestrates the two-pass portfolio review pipeline.
    """
    structured_llm = llm.with_structured_output(PortfolioCritique)

    # 1: Instant Backend Math & Regex
    backend_findings = run_deterministic_checks(portfolio)
    
    # 2: Qualitative LLM Analysis
    llm_findings = generate_llm_critique(portfolio, backend_findings,structured_llm)
    
    return {
        "status": "Review Complete",
        "deterministic_flags": backend_findings,
        "ai_critic_suggestions": llm_findings
    }
