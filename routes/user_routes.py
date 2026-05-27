from fastapi import APIRouter, HTTPException
from models.schemas import UserSignup, UserLogin, FullUserProfile
from services.user_service import create_user, verify_login, get_full_profile

router = APIRouter()

@router.post("/signup")
async def signup_endpoint(payload: UserSignup):
    """Frontend Action: Registers a new user."""
    try:
        user = await create_user(payload)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login_endpoint(payload: UserLogin):
    """Frontend Action: Logs a user in and returns their safe profile data."""
    try:
        user = await verify_login(payload)
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/profile", response_model=FullUserProfile)
async def fetch_user_profile_endpoint(user_id: str):
    """
    Frontend Action: Renders the profile page.
    Returns the user's name/email, and embeds their entire portfolio, 
    individual reviews, and overall rating if they are a freelancer.
    """
    try:
        profile_data = await get_full_profile(user_id)
        return profile_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))