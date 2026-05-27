from models.schemas import ClientReview
from utils.database import review_collection, client_request_collection
from utils.validator import validate_user_exists
import uuid
from fastapi import HTTPException

async def create_review(review_data: ClientReview) -> dict:
    """Saves a standalone review to the database after verifying client ownership."""
    review_dict = review_data.model_dump(mode="json")
    
    project_id = review_dict.get("project_id")
    client_id = review_dict.get("client_id")
    
    await validate_user_exists(client_id)

    # 1. Fetch the project to verify it exists
    project = await client_request_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project ID does not exist.")
        
    # 2. Verify the client submitting the review actually owns this project
    if project.get("client_id") != client_id:
        raise HTTPException(
            status_code=403, 
            detail="Unauthorized: You cannot review a project that belongs to a different client."
        )

    # 3. Add the unique review ID
    review_dict["review_id"] = str(uuid.uuid4())
    
    # 4. Save to database
    await review_collection.insert_one(review_dict)
    
    review_dict.pop("_id", None)
    return review_dict


async def get_freelancer_received_reviews(freelancer_id: str) -> list:
    """
    Fetches all reviews a specific freelancer has received.
    Useful for displaying on the freelancer's public profile.
    """
    # 1. Verify the freelancer actually exists
    await validate_user_exists(freelancer_id)
    
    # 2. Fetch the reviews, sorted newest first
    cursor = review_collection.find({"freelancer_id": freelancer_id}).sort("created_at", -1)
    reviews = await cursor.to_list(length=100)
    
    # 3. Clean up the MongoDB Object ID before returning
    for review in reviews:
        review.pop("_id", None)
        
    return reviews


async def get_client_sent_reviews(client_id: str) -> list:
    """
    Fetches all reviews a specific client has submitted.
    Useful for the client's internal dashboard/history.
    """
    # 1. Verify the client actually exists
    await validate_user_exists(client_id)
    
    # 2. Fetch the reviews, sorted newest first
    cursor = review_collection.find({"client_id": client_id}).sort("created_at", -1)
    reviews = await cursor.to_list(length=100)
    
    # 3. Clean up the MongoDB Object ID before returning
    for review in reviews:
        review.pop("_id", None)
        
    return reviews