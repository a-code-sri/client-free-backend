import re
from datetime import datetime, timezone
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv

import json
from langchain_core.prompts import PromptTemplate

BADGE_WEIGHTS = {
    "Top Rated": 1.0,
    "Elite Developer": 0.9,
    "Flawless Success": 0.8,
    "Skill Assessed": 0.7,
    "Rising Talent": 0.6,
    "Fast Responder": 0.4,
    "Creative Thinker": 0.05,
    "Problem Solver": 0.05,
    "Design Champion": 0.05,
    "Code Ninja": 0.05
}

def get_best_project_via_vector(project_desc: str, freelancer_projects: List[Dict],embeddings) -> Dict:
    if not freelancer_projects:
        return None
    docs = []
    for proj in freelancer_projects:
        content = f"Title: {proj.get('title', '')}\nDescription: {proj.get('description', '')}\nTech Stack: {', '.join(proj.get('tech_stack', []))}"
        docs.append(Document(page_content=content))
    vectorstore = FAISS.from_documents(docs, embeddings)
    results = vectorstore.similarity_search(project_desc, k=1)

    if results and len(results) > 0:
        return results[0].page_content
    return None


def get_llm_relevance_score(client_project_desc: str, freelancer_project_text: str,llm) -> float:

    prompt_template = PromptTemplate.from_template("""
    You are an expert technical recruiter evaluating a freelancer's portfolio project against a client's requirements.
    
    Client Requirements:
    {client}
    
    Freelancer's Past Project:
    {freelancer}
    
    Calculate a relevance score between 0.0 (completely irrelevant) and 1.0 (perfect match).
    You MUST respond with a valid JSON object in this exact format: {{"score": 0.85}}
    Do not include markdown blocks or any other text.
    """)

    prompt = prompt_template.format(client=client_project_desc, freelancer=freelancer_project_text)
    try:
        response = llm.invoke(prompt)
        
        clean_json = response.content.replace("```json", "").replace("```", "").strip()

        score_data = json.loads(clean_json)
        return float(score_data.get("score", 0.0))
        
    except Exception as e:
        print(f"LLM Scoring Failed: {e}")
        return 0.0

def extract_weekly_hours(availability_str: str) -> int:
    if "Unavailable" in availability_str:
        return 0
    match = re.search(r'(\d+)', availability_str)
    return int(match.group(1)) if match else 0

def passes_hard_constraints(freelancer: Dict[str, Any], project: Dict[str, Any], current_date: datetime) -> bool:
    weekly_hours = extract_weekly_hours(freelancer.get("availability_status", ""))
    
    if weekly_hours == 0:
        return False
        
    freelancer_rate = freelancer.get("hourly_rate", 0)
    budget_range = project.get("budget_range", {"min": 0, "max": 0})
    
    if project.get("project_type") == "Hourly":
        max_acceptable_rate = budget_range["max"] * 1.2
        if freelancer_rate > max_acceptable_rate:
            return False
            
    elif project.get("project_type") == "Fixed":
        deadline_str = project.get("deadline")
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        
        days_to_deadline = (deadline - current_date).days
        weeks_to_deadline = max(1, days_to_deadline / 7)
        
        max_capacity_cost = weeks_to_deadline * weekly_hours * freelancer_rate
        
        if max_capacity_cost < (budget_range["min"] * 0.5):
            return False
            
    return True

def calculate_match_score(freelancer: Dict[str, Any], project: Dict[str, Any], embeddings, llm) -> float:
    rating = freelancer.get("rating", 4.0) 
    active_days = freelancer.get("active_days_per_week", 5) 
    badges = freelancer.get("badges", []) 
    description = project.get("description", "")
    
    best_project_doc = get_best_project_via_vector(description, freelancer.get("projects", []), embeddings)
    if best_project_doc:
        llm_score = get_llm_relevance_score(description, best_project_doc, llm)
    else:
        llm_score = 0.0

    weighted_project = llm_score * 0.35 
    
    required_skills = set(project.get("required_skills", []))
    freelancer_skills = set(freelancer.get("skills", []))
    
    if required_skills:
        skill_overlap = len(required_skills.intersection(freelancer_skills)) / len(required_skills)
    else:
        skill_overlap = 1.0
        
    weighted_skill = skill_overlap * 0.30
    
    normalized_rating = (rating / 5.0) * 0.15
    
    normalized_active = (active_days / 7.0) * 0.10
    
    total_badge_weight = sum(BADGE_WEIGHTS.get(badge, 0.1) for badge in badges)
    
    TARGET_WEIGHT_CAP = 1.5 
    badge_multiplier = min(total_badge_weight / TARGET_WEIGHT_CAP, 1.0)
    
    weighted_badges = badge_multiplier * 0.10
    
    final_score = weighted_project + weighted_skill + normalized_rating + normalized_active + weighted_badges
    return round(final_score, 4)

def execute_smart_match(project: Dict[str, Any], all_freelancers: List[Dict[str, Any]],embeddings,llm) -> List[Dict[str, Any]]:
    current_date = datetime.now(timezone.utc)
    scored_candidates = []
    load_dotenv()
    
    for freelancer in all_freelancers:
        if not passes_hard_constraints(freelancer, project, current_date):
            continue
            
        score = calculate_match_score(freelancer, project,embeddings,llm)
        
        scored_candidates.append({
            "freelancer_id": freelancer["user_id"],
            "match_score": score,
            "bio": freelancer["bio"]
        })
        
    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_candidates[:5]


