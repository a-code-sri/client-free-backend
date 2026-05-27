from models.schemas import FreelancerPortfolio
from utils.database import freelancer_portfolio_collection
from typing import List
from utils.validator import validate_user_exists

async def get_portfolio(user_id: str) -> dict:
    """Fetches a freelancer's portfolio by their User ID."""
    await validate_user_exists(user_id)
    portfolio = await freelancer_portfolio_collection.find_one({"user_id": user_id})
    
    if portfolio:
        portfolio.pop("_id", None)
    return portfolio

async def upsert_portfolio(user_id: str, portfolio_data: FreelancerPortfolio) -> dict:
    """Creates a new portfolio or overwrites an existing one."""
    await validate_user_exists(user_id)
    portfolio_dict = portfolio_data.model_dump(mode="json")
    
    portfolio_dict["user_id"] = user_id 

    await freelancer_portfolio_collection.update_one(
        {"user_id": user_id},
        {"$set": portfolio_dict},
        upsert=True
    )
    
    return portfolio_dict

async def bulk_upsert_portfolios(portfolios_data: List[FreelancerPortfolio]) -> dict:
    """Admin tool: Seeds the database with an array of portfolios."""
    inserted_count = 0
    
    for portfolio in portfolios_data:
        portfolio_dict = portfolio.model_dump(mode="json")
        user_id = portfolio_dict["user_id"]
        await validate_user_exists(user_id)
        await freelancer_portfolio_collection.update_one(
            {"user_id": user_id},
            {"$set": portfolio_dict},
            upsert=True
        )
        inserted_count += 1
        
    return {"message": f"Successfully processed {inserted_count} portfolios."}