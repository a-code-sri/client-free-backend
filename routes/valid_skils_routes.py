from fastapi import APIRouter, HTTPException
from utils.database import verified_skills

router = APIRouter()

@router.post("/show_valid_skills/{user_id}")
async def show_valid_skills(user_id: str):
    """Returns valid_skills. Creates an empty document for the user if not found."""
    try:
        document = await verified_skills.find_one({"user_id": user_id})
        if not document:
            document = {
                "user_id": user_id,
                "verified_skills": [] 
            }
            await verified_skills.insert_one(document.copy())
        
        document.pop("_id", None)
        return document

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))