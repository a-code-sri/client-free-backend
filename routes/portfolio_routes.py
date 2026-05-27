from fastapi import APIRouter, HTTPException
from models.schemas import FreelancerPortfolio
from services.portfolio_service import get_portfolio, upsert_portfolio,bulk_upsert_portfolios
from typing import List
router = APIRouter()

@router.get("/{user_id}", response_model=FreelancerPortfolio)
async def fetch_portfolio(user_id: str):
    """Retrieves a freelancer's full portfolio."""
    portfolio = await get_portfolio(user_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found for this user.")
    return portfolio

@router.put("/{user_id}", response_model=FreelancerPortfolio)
async def update_portfolio(user_id: str, portfolio: FreelancerPortfolio):
    """Creates or updates the freelancer's portfolio."""
    try:
        updated_portfolio = await upsert_portfolio(user_id, portfolio)
        return updated_portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-upload")
async def bulk_upload_portfolios(portfolios: List[FreelancerPortfolio]):
    """Admin tool: Seed the database with multiple portfolios at once."""
    try:
        result = await bulk_upsert_portfolios(portfolios)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))