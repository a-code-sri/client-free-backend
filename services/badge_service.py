from utils.database import (
    user_collection as users_collection,
    review_collection, 
    contract_collection,
    transaction_collection
)
from models.schemas import ProjectStatus

async def evaluate_freelancer_badges(user_id: str) -> list:
    """Calculates which badges a freelancer qualifies for based on their stats."""
    
    rev_cursor = review_collection.find({"reviewee_id": user_id})
    reviews = await rev_cursor.to_list(length=None)
    
    total_reviews = len(reviews)
    rating = sum(r["stars"] for r in reviews) / total_reviews if total_reviews > 0 else 0.0

    completed_contracts = await contract_collection.count_documents({
        "freelancer_id": user_id, 
        "status": ProjectStatus.completed
    })
    cancelled_contracts = await contract_collection.count_documents({
        "freelancer_id": user_id, 
        "status": ProjectStatus.cancelled
    })
    
    tx_cursor = transaction_collection.find({"freelancer_id": user_id, "type": "Earning"})
    transactions = await tx_cursor.to_list(length=None)
    total_earnings = sum(tx["amount"] for tx in transactions)

    earned_badges = set()

    if rating >= 4.8 and completed_contracts >= 15:
        earned_badges.add("Top Rated")

    if rating >= 4.9 and (completed_contracts >= 30 or total_earnings >= 10000):
        earned_badges.add("Elite Developer")

    if completed_contracts >= 5 and cancelled_contracts == 0:
        earned_badges.add("Flawless Success")

    if 4.5 <= rating < 4.8 and 1 <= completed_contracts <= 5:
        earned_badges.add("Rising Talent")

  
    return list(earned_badges)


async def run_system_badge_assignment():
    """Background task to loop through all freelancers and assign earned badges."""
    
    cursor = users_collection.find({"role": {"$in": ["Freelancer", "Both"]}})
    freelancers = await cursor.to_list(length=None)
    
    for freelancer in freelancers:
        user_id = freelancer["user_id"]
        new_badges = await evaluate_freelancer_badges(user_id)
        
        if new_badges:
            await users_collection.update_one(
                {"user_id": user_id},
                {"$addToSet": {
                    "badges": {"$each": new_badges}
                }}
            )
            
    print(f"Successfully processed badge assignments for {len(freelancers)} freelancers.")