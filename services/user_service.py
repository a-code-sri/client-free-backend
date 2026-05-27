import hashlib
import uuid
from pymongo.errors import DuplicateKeyError
from models.schemas import UserSignup, UserLogin, UserInDB
from utils.database import user_collection, freelancer_portfolio_collection, review_collection

async def setup_database_indexes():
    """
    Run this function once when your FastAPI app starts.
    It tells MongoDB to permanently reject any duplicate user_ids or emails.
    """
    await user_collection.create_index("user_id", unique=True)
    await user_collection.create_index("email", unique=True)
    await freelancer_portfolio_collection.create_index("user_id", unique=True)

def hash_password(password: str) -> str:
    """Simple, dependency-free password hashing for hackathons."""
    return hashlib.sha256(password.encode()).hexdigest()

async def create_user(user_data: UserSignup) -> dict:
    """Registers a new user securely with DB-level uniqueness."""

    existing_user = await user_collection.find_one({"email": user_data.email})
    if existing_user:
        raise ValueError("Email is already registered")

    new_user = UserInDB(
        user_id=str(uuid.uuid4()),
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        student_id=user_data.student_id,
        linkedin_url=str(user_data.linkedin_url) if user_data.linkedin_url else None,
        hashed_password=hash_password(user_data.password)
    )

    try:
        await user_collection.insert_one(new_user.model_dump())
        if user_data.role in ["Freelancer", "Both"]:
            await freelancer_portfolio_collection.insert_one({
                "user_id": new_user.user_id,
                "bio": "",
                "skills": [],
                "hourly_rate": 0.0,
                "availability_status": "Not available",
                "education": [],
                "work_experience": [],
                "projects": []
            })
    except DuplicateKeyError:
        raise ValueError("A user with this Email or User ID already exists.")
    
    safe_user = new_user.model_dump()
    safe_user.pop("hashed_password", None)
    return safe_user

async def verify_login(login_data: UserLogin) -> dict:
    """Verifies email and password, returning the user profile (including user_id)."""
    hashed_attempt = hash_password(login_data.password)
    user = await user_collection.find_one({
        "email": login_data.email,
        "hashed_password": hashed_attempt
    })
    
    if not user:
        raise ValueError("Invalid email or password")
        
    user.pop("_id", None)  
    user.pop("hashed_password", None)
    
    
    return user

async def get_full_profile(user_id: str) -> dict:
    """Fetches user, portfolio, AND calculates reviews dynamically."""
    
    user = await user_collection.find_one({"user_id": user_id})
    if not user:
        raise ValueError("User not found")
        
    user.pop("_id", None)
    user.pop("hashed_password", None) 

    role = user.get("role", "")
    if isinstance(role, str) and role.lower() == "freelancer":
        
        portfolio = await freelancer_portfolio_collection.find_one({"user_id": user_id})
        if portfolio:
            portfolio.pop("_id", None)
            user["portfolio"] = portfolio
        else:
            user["portfolio"] = None 

        cursor = review_collection.find({"freelancer_id": user_id})
        reviews = await cursor.to_list(length=100)
        
        for r in reviews:
            r.pop("_id", None)
            
        user["reviews"] = reviews

        if reviews:
            total_stars = sum(r["stars"] for r in reviews)
            user["rating"] = round(total_stars / len(reviews), 1)
        else:
            user["rating"] = 0.0
            
    else:
        user["portfolio"] = None
        user["reviews"] = []
        user["rating"] = 0.0

    return user