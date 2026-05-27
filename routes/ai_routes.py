from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any
from ai.evaluate_proposal import evaluate_proposal
from ai.scope_project import scope_project_pipeline
from ai.review_portfolio import review_portfolio
from ai.match_freelancers import execute_smart_match
from ai.taxonomy import HARDCODED_SKILL_TAXONOMY
from services.portfolio_rating_stitch import fetch_and_stitch_portfolios

from langchain_groq import ChatGroq
from models.schemas import TestGenerationRequest, TestSubmissionRequest
from services.evaluate_skilltest import submit_test_for_evaluation
from ai.generate_skill_test import generate_and_save_skill_test
from dotenv import load_dotenv
from utils.database import user_collection, skill_test_collection

load_dotenv()

router = APIRouter()

# ✅ Use Groq only (Remote LLM, no local model memory)
try:
    llm = ChatGroq(model="llama-3.3-70b-versatile")
except Exception as e:
    print(f"Warning: Failed to load AI model. Error: {e}")
    llm = None

VALID_SKILLS_DB = list(HARDCODED_SKILL_TAXONOMY.keys())


# ✅ Authorization dependency
async def verify_user_authorized(x_user_id: str = Header(...)):
    user = await user_collection.find_one({"user_id": x_user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


# ✅ Evaluate Proposal
@router.post("/evaluate-proposal")
async def evaluate_proposal_endpoint(payload: Dict[str, Any],
                                     user=Depends(verify_user_authorized)):
    if not llm:
        raise HTTPException(status_code=500, detail="AI model not initialized")

    try:
        result = evaluate_proposal(
            proposal=payload["proposal"],
            project=payload["project"],
            llm=llm
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Scope Project
@router.post("/scope-project")
async def scope_project_endpoint(payload: Dict[str, Any],
                                 user=Depends(verify_user_authorized)):

    if not llm:
        raise HTTPException(status_code=500, detail="AI model not initialized")

    try:
        result = scope_project_pipeline(
            client_input=payload["client_input"],
            generator_llm=llm,
            VALID_SKILLS_DB=VALID_SKILLS_DB
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Review Portfolio
@router.post("/review-portfolio")
async def review_portfolio_endpoint(payload: Dict[str, Any],
                                    user=Depends(verify_user_authorized)):

    if not llm:
        raise HTTPException(status_code=500, detail="AI model not initialized")

    try:
        result = review_portfolio(
            portfolio=payload["portfolio"],
            llm=llm
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Match Freelancers (LLM-only, no embeddings)
@router.post("/match-freelancers")
async def match_freelancers_endpoint(payload: Dict[str, Any],
                                     user=Depends(verify_user_authorized)):

    if not llm:
        raise HTTPException(status_code=500, detail="AI model not initialized")

    try:
        stitched_freelancers = await fetch_and_stitch_portfolios()

        if not stitched_freelancers:
            return {"matches": []}

        # ✅ Use LLM-only ranking (no embeddings)
        top_candidates = execute_smart_match(
            project=payload["project"],
            all_freelancers=stitched_freelancers,
            llm=llm
        )

        return {"matches": top_candidates}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Generate Skill Test
@router.post("/generate-skilltest")
async def generate_test_endpoint(payload: TestGenerationRequest,
                                 user=Depends(verify_user_authorized)):
    try:
        return await generate_and_save_skill_test(
            payload.user_id,
            payload.skill,
            llm
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Submit Test
@router.post("/submit-test")
async def submit_test_endpoint(payload: TestSubmissionRequest,
                               user=Depends(verify_user_authorized)):
    try:
        result = await submit_test_for_evaluation(
            test_id=payload.test_id,
            user_id=payload.user_id,
            user_answers=payload.user_answers,
            llm=llm
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Valid Skills
@router.post("/valid_skills")
async def skills():
    return list(HARDCODED_SKILL_TAXONOMY.keys())
