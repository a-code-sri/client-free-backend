import random
from utils.database import (
    freelancer_portfolio_collection, 
    review_collection, 
    user_collection as users_collection
)

async def fetch_and_stitch_portfolios() -> list:
    """Fetches portfolios, stitches ratings/badges, returning top 500 + 500 random."""
    
    cursor = freelancer_portfolio_collection.find({})
    all_portfolios = await cursor.to_list(length=None) 
    
    for freelancer in all_portfolios:
        freelancer.pop("_id", None)
        user_id = freelancer.get("user_id")
        
        rev_cursor = review_collection.find({"freelancer_id": user_id})
        reviews = await rev_cursor.to_list(length=100)
        
        if reviews:
            total_stars = sum(r["stars"] for r in reviews)
            freelancer["rating"] = round(total_stars / len(reviews), 1)
        else:
            freelancer["rating"] = 4.0 
            
        user_doc = await users_collection.find_one({"user_id": user_id})
        freelancer["badges"] = user_doc.get("badges", []) if user_doc else []

    all_portfolios.sort(key=lambda x: x.get("rating", 0), reverse=True)
    
    top_50 = all_portfolios[:50]
    remaining = all_portfolios[50:]
    random_50 = random.sample(remaining, min(50, len(remaining)))
    
    final_list = top_50 + random_50
    
    return final_list