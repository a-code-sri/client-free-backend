from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any
from ai.evaluate_proposal import evaluate_proposal
from ai.scope_project import scope_project_pipeline 
from ai.review_portfolio import review_portfolio
from ai.match_freelancers import execute_smart_match
from ai.taxonomy import HARDCODED_SKILL_TAXONOMY
from services.portfolio_rating_stitch import fetch_and_stitch_portfolios

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from models.schemas import TestGenerationRequest, TestSubmissionRequest
from services.evaluate_skilltest import  submit_test_for_evaluation
from ai.generate_skill_test import generate_and_save_skill_test
from dotenv import load_dotenv
from utils.database import user_collection,skill_test_collection


load_dotenv()

router = APIRouter()
try:
    #llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
    llm = ChatGroq(model="llama-3.3-70b-versatile",)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
except Exception as e:
    print("rooutes")
    print(f"Warning: Failed to load AI models. Error: {e}")
    llm = None
    embeddings = None


VALID_SKILLS_DB = list(HARDCODED_SKILL_TAXONOMY.keys())



class MCQQuestion(BaseModel):
    subtopic: str = Field(description="The specific subtopic being tested.")
    question_text: str = Field(description="The technical multiple-choice question.")
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str = Field(description="Must be exactly 'A', 'B', 'C', or 'D'.")
    explanation: str = Field(description="Brief explanation of why the answer is correct for the analysis report.")

class EvaluationPayload(BaseModel):
    proposal: Dict[str, Any]
    project: Dict[str, Any]

class ScopePayload(BaseModel):
    client_input: str

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

class PortfolioReviewPayload(BaseModel):
    portfolio: Dict[str, Any]

class Project(BaseModel):
    project: Dict[str, Any]
class GenerateTestPayload(BaseModel):
    skill: str

class EvaluateTestPayload(BaseModel):
    test_id: str
    questions: List[Dict[str, Any]]
    user_answers: Dict[str, str]

async def verify_user_authorized(x_user_id: str = Header(..., description="The User ID to authorize the request")):
    """
    Checks the database to ensure the user exists. 
    If they don't, it blocks the request and returns a 401 Unauthorized.
    """
    user = await user_collection.find_one({"user_id": x_user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: User ID not found.")
    return user

@router.post("/evaluate-proposal")
async def evaluate_proposal_endpoint(payload: EvaluationPayload,user = Depends(verify_user_authorized)):
    if not llm or not embeddings:
        raise HTTPException(status_code=500, detail="AI models not initialized.")
    try:
        result = evaluate_proposal(
            proposal=payload.proposal, 
            project=payload.project,
            llm=llm,
            embeddings=embeddings
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scope-project")
async def scope_project_endpoint(payload: ScopePayload,user = Depends(verify_user_authorized)):
    """
    AI Endpoint: Validates and scopes a client's vague project idea.
    Implements a two-step Agentic routing process.
    """
    if not llm:
        raise HTTPException(status_code=500, detail="AI models not initialized.")
    try:
        result = scope_project_pipeline(
            client_input=payload.client_input,
            generator_llm=llm,
            VALID_SKILLS_DB=VALID_SKILLS_DB
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/review-portfolio")
async def review_portfolio_endpoint(payload: PortfolioReviewPayload,user = Depends(verify_user_authorized)):
    """
    AI Endpoint: Audits a freelancer's portfolio using a two-pass system:
    1. Deterministic regex/structural checks.
    2. LLM qualitative critique and rate evaluation.
    """
    if not llm:
        raise HTTPException(status_code=500, detail="AI models not initialized.")
        
    try:
        result = review_portfolio(
            portfolio=payload.portfolio, 
            llm=llm
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-freelancers")
async def match_freelancers_endpoint(payload: Project,user = Depends(verify_user_authorized)):
    if not llm or not embeddings:
        raise HTTPException(status_code=500, detail="AI models not initialized.")
        
    try:
        stitched_freelancers = await fetch_and_stitch_portfolios()
        
        if not stitched_freelancers:
            return {"message": "No freelancers available to match."}
        top_candidates = execute_smart_match(
            project=payload.project,
            all_freelancers=stitched_freelancers, 
            embeddings=embeddings,
            llm=llm
        )
        
        return {"matches": top_candidates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-skilltest")
async def generate_test_endpoint(payload: TestGenerationRequest,user = Depends(verify_user_authorized)):
    """Creates a new test, saves the answers, and returns the questions."""
    try:
        test_data = await generate_and_save_skill_test(payload.user_id, payload.skill, llm)
        return test_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-test")
async def submit_test_endpoint(payload: TestSubmissionRequest,user = Depends(verify_user_authorized)):
    """Evaluates the submitted answers against the database records."""
    try:
        test_id=payload.test_id
        user = await skill_test_collection.find_one({"test_id": test_id})
        if not user:
            raise HTTPException(status_code=408, detail="Unauthorized: Test ID not found.")

        result = await submit_test_for_evaluation(
            test_id=payload.test_id, 
            user_id=payload.user_id, 
            user_answers=payload.user_answers,
            llm=llm
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/valid_skills")
async def skills():
    """Returns skills in database."""
    try:
        result=list(HARDCODED_SKILL_TAXONOMY.keys())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))