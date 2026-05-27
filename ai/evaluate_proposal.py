import json
import math
from typing import Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

def get_cosine_similarity(proposal_text: str, project_desc: str,embeddings) -> float:
    """Calculates semantic distance between the proposal and project description."""
    if not proposal_text or not project_desc:
        return 0.0
        
    doc = Document(page_content=proposal_text)
    vectorstore = FAISS.from_documents([doc], embeddings)
    results = vectorstore.similarity_search_with_relevance_scores(project_desc, k=1)
    
    if results:
        score = results[0][1]
        return max(0.0, min(1.0, float(score)))
    return 0.0
def get_llm_metrics(proposal: Dict[str, Any], project: Dict[str, Any],llm) -> Dict[str, float]:
    """Forces the LLM to output exact floats for relevance and clarity, now factoring in milestones."""

    milestones = proposal.get("proposed_milestones", [])
    milestone_text = "None provided."
    if milestones:
        milestone_text = "\n".join(
            [f"- {m.get('title', 'Task')}: ${m.get('amount', 0)} (Due: {m.get('due_date', 'N/A')})" for m in milestones]
        )

    prompt_template = PromptTemplate.from_template("""
    You are evaluating a freelancer's proposal against a client's project.
    
    Project Title: {title}
    Project Description: {desc}
    
    Freelancer Proposal (Cover Letter):
    {proposal}
    
    Proposed Milestones:
    {milestones}
    
    Evaluate two metrics from 0.0 (terrible) to 1.0 (perfect):
    1. 'llm_relevance': How accurately does the proposal address the specific project needs?
    2. 'clarity': How clear, professional, and well-structured is the proposal? (Heavily weigh the presence and logic of the Proposed Milestones here. Good milestones = high clarity).
    
    Respond STRICTLY in JSON format: {{"llm_relevance": 0.85, "clarity": 0.90}}
    """)
    
    prompt = prompt_template.format(
        title=project.get("title", ""),
        desc=project.get("description", ""),
        proposal=proposal.get("cover_letter", ""),
        milestones=milestone_text
    )
    
    try:
        response = llm.invoke(prompt)
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        return {
            "llm_relevance": float(data.get("llm_relevance", 0.0)),
            "clarity": float(data.get("clarity", 0.0))
        }
    except Exception as e:
        print(f"LLM Parsing Error: {e}")
        return {"llm_relevance": 0.0, "clarity": 0.0}

def evaluate_proposal(proposal: Dict[str, Any], project: Dict[str, Any],llm,embeddings) -> Dict[str, Any]:

    bid_amount = float(proposal.get("bid_amount", 0.0))
    max_budget = float(project.get("budget_range", {}).get("max", 0.0))
    
    cosine_score = get_cosine_similarity(proposal.get("cover_letter", ""), project.get("description", ""),embeddings)
    llm_data = get_llm_metrics(proposal, project,llm)

    relevance = (0.6 * cosine_score) + (0.4 * llm_data["llm_relevance"])

    quality = (0.7 * relevance) + (0.3 * llm_data["clarity"])
    
    overshoot_ratio = 2.0
    
    if bid_amount > max_budget and max_budget > 0:
        penalty_factor = overshoot_ratio * ((bid_amount - max_budget) / max_budget)
        price_penalty = min(1.0, penalty_factor)
    else:
        price_penalty = 0.0
    final_score = quality * (1.0 - price_penalty)
        
    return {
        "proposal_id": proposal.get("proposal_id"),
        "final_score": round(final_score, 4),
        "breakdown": {
            "relevance": round(relevance, 4),
            "clarity":round(llm_data["clarity"],4),
            "quality": round(quality, 4),
            "price_penalty": round(price_penalty, 4)
        }
    }