from fastapi import APIRouter, HTTPException
from models.schemas import ClientReview
from services.review_service import (
    create_review,
    get_freelancer_received_reviews,
    get_client_sent_reviews
)

router = APIRouter()

@router.post("/")
async def submit_review_endpoint(payload: ClientReview):
    """
    Frontend Action: Client submits a review for a completed project.
    """
    try:
        result = await create_review(payload)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/freelancer/{freelancer_id}")
async def get_freelancer_reviews_endpoint(freelancer_id: str):
    """
    Frontend Action: Loads a Freelancer's public profile.
    Fetches all reviews this freelancer has received.
    """
    try:
        reviews = await get_freelancer_received_reviews(freelancer_id)
        return {"reviews": reviews}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/client/{client_id}")
async def get_client_reviews_endpoint(client_id: str):
    """
    Frontend Action: Loads the Client's internal dashboard.
    Fetches all reviews this client has previously written.
    """
    try:
        reviews = await get_client_sent_reviews(client_id)
        return {"reviews": reviews}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))