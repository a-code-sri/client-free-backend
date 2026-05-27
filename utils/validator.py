from fastapi import HTTPException
from utils.database import user_collection

async def validate_user_exists(user_id: str) -> dict:
    """
    Use this for actions (like posting a project or bidding).
    Throws a 404 if the user is not found in the database.
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required.")
        
    user = await user_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' does not exist.")
        
    return user

async def validate_user_is_unique(email: str) -> None:
    """
    Use this strictly for REGISTRATION.
    Throws a 409 Conflict if the email is already in use.
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required for registration.")
        
    existing_user = await user_collection.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")