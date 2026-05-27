from utils.database import feed_collection, challenge_collection, mentorship_collection
from utils.database import user_collection as users_collection
from datetime import datetime, timezone, timedelta
import uuid

async def verify_user_exists(user_id: str):
    """Raises ValueError if the user does not exist in the database."""
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        raise ValueError(f"User ID '{user_id}' does not exist.")

async def verify_session_exists(session_id: str):
    """Returns the session or raises ValueError if it does not exist."""
    session = await mentorship_collection.find_one({"session_id": session_id})
    if not session:
        raise ValueError(f"Mentorship session '{session_id}' not found.")
    return session

async def create_feed_post(payload) -> dict:
    await verify_user_exists(payload.author_id)
    
    post_dict = {
        "post_id": f"post_{uuid.uuid4().hex[:8]}",
        "author_id": payload.author_id,
        "content": payload.content,
        "tags": payload.tags,
        "liked_by": [], 
        "comments": [], 
        "created_at": datetime.now(timezone.utc)
    }
    await feed_collection.insert_one(post_dict)
    post_dict.pop("_id", None)
    return post_dict




async def get_public_feed(limit: int = 50) -> list:
    """Fetches the latest community posts."""
    cursor = feed_collection.find().sort("created_at", -1).limit(limit)
    posts = await cursor.to_list(length=limit)
    for p in posts:
        p.pop("_id", None)
    return posts

async def toggle_like_post(post_id: str, user_id: str) -> dict:
    """Toggles a like on a community post. Prevents double-liking."""
    await verify_user_exists(user_id)
    
    post = await feed_collection.find_one({"post_id": post_id})
    if not post:
        raise ValueError("Post not found.")

    if user_id in post.get("liked_by", []):
        await feed_collection.update_one(
            {"post_id": post_id},
            {"$pull": {"liked_by": user_id}}
        )
        return {"message": "Post unliked.", "is_liked": False}
    else:
        await feed_collection.update_one(
            {"post_id": post_id},
            {"$addToSet": {"liked_by": user_id}}
        )
        return {"message": "Post liked.", "is_liked": True}

# --- 2. MENTORSHIP LOGIC ---
async def create_mentorship_offer(payload) -> dict:
    await verify_user_exists(payload.mentor_id)
    
    session_dict = {
        "session_id": f"ment_{uuid.uuid4().hex[:8]}",
        "mentor_id": payload.mentor_id,
        "title": payload.title,
        "description": payload.description,
        "price": payload.price,
        "duration_minutes": payload.duration_minutes,
        "available_slots": payload.available_slots,
        "booked_by": [], 
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    await mentorship_collection.insert_one(session_dict)
    session_dict.pop("_id", None)
    return session_dict

async def book_mentorship_session(session_id: str, mentee_id: str) -> dict:
    """Mentee books an available slot."""
    await verify_user_exists(mentee_id)
    session = await verify_session_exists(session_id)
    
    if session["available_slots"] <= 0:
        raise ValueError("This mentorship session is fully booked.")
        
    if mentee_id in session.get("booked_by", []):
        raise ValueError("You have already booked this session.")

    await mentorship_collection.update_one(
        {"session_id": session_id},
        {
            "$inc": {"available_slots": -1},
            "$addToSet": {"booked_by": mentee_id}
        }
    )
    return {"message": "Mentorship session booked successfully!"}

async def get_user_mentorship_details(user_id: str) -> dict:
    """Retrieves all sessions offered by and booked by a specific user."""
    await verify_user_exists(user_id)
    
    # Get sessions the user is offering
    offered_cursor = mentorship_collection.find({"mentor_id": user_id}).sort("created_at", -1)
    offered_sessions = await offered_cursor.to_list(length=100)
    for s in offered_sessions:
        s.pop("_id", None)
        
    # Get sessions the user has booked
    booked_cursor = mentorship_collection.find({"booked_by": user_id}).sort("created_at", -1)
    booked_sessions = await booked_cursor.to_list(length=100)
    for s in booked_sessions:
        s.pop("_id", None)
        
    return {
        "user_id": user_id,
        "offered_sessions": offered_sessions,
        "booked_sessions": booked_sessions
    }

# --- 3. SKILL CHALLENGES LOGIC ---
async def create_weekly_challenge(payload) -> dict:
    """User or Admin creates a new community challenge."""
    await verify_user_exists(payload.creator_id)
    
    challenge_dict = {
        "challenge_id": f"chal_{uuid.uuid4().hex[:8]}",
        "creator_id": payload.creator_id,
        "title": payload.title,
        "description": payload.description,
        "reward_badge": payload.reward_badge,
        "deadline": datetime.now(timezone.utc) + timedelta(days=payload.deadline_days),
        "is_active": True,
        "submissions": [],
        "winner_id": None, 
        "created_at": datetime.now(timezone.utc)
    }
    await challenge_collection.insert_one(challenge_dict)
    challenge_dict.pop("_id", None)
    return challenge_dict

async def submit_to_challenge(payload) -> dict:
    """Freelancer submits their project URL to the challenge."""
    await verify_user_exists(payload.freelancer_id)
    
    challenge = await challenge_collection.find_one({"challenge_id": payload.challenge_id})
    if not challenge:
        raise ValueError(f"Challenge '{payload.challenge_id}' does not exist.")
    if not challenge.get("is_active"):
        raise ValueError("This challenge is no longer active.")

    for sub in challenge.get("submissions", []):
        if sub["freelancer_id"] == payload.freelancer_id:
            raise ValueError("You have already submitted to this challenge.")

    submission = {
        "freelancer_id": payload.freelancer_id,
        "submission_url": str(payload.submission_url),
        "description": payload.description,
        "upvotes": 0,
        "submitted_at": datetime.now(timezone.utc)
    }

    await challenge_collection.update_one(
        {"challenge_id": payload.challenge_id},
        {"$push": {"submissions": submission}}
    )
    return {"message": "Project submitted successfully! Good luck."}

async def upvote_submission(challenge_id: str, freelancer_id: str) -> dict:
    """Community members vote for the best submission."""
    await verify_user_exists(freelancer_id)
    
    result = await challenge_collection.update_one(
        {
            "challenge_id": challenge_id, 
            "submissions.freelancer_id": freelancer_id
        },
        {
            "$inc": {"submissions.$.upvotes": 1}
        }
    )
    
    if result.modified_count == 0:
        raise ValueError("Submission or Challenge not found.")
        
    return {"message": "Upvote recorded!"}

async def get_active_challenges() -> list:
    """Fetches all ongoing challenges. Shows only the top submission if the creator selected one."""
    cursor = challenge_collection.find({"is_active": True}).sort("created_at", -1)
    challenges = await cursor.to_list(length=10)
    
    for c in challenges:
        c.pop("_id", None)
        submissions = c.get("submissions", [])
        
        top_candidate_id = c.get("top_candidate_id")
        
        if top_candidate_id:
            c["submissions"] = [sub for sub in submissions if sub["freelancer_id"] == top_candidate_id]
        else:
            c["submissions"] = sorted(submissions, key=lambda x: x.get("upvotes", 0), reverse=True)
            
    return challenges



async def get_user_posts(user_id) -> dict:

    await verify_user_exists(user_id)
    cursor = feed_collection.find({"author_id": user_id}).sort("created_at", -1)
    posts = await cursor.to_list(length=100)
    
    for post in posts:
        post.pop("_id", None)
        
    return posts

async def get_active_methorships() -> dict:

    cursor = mentorship_collection.find({"is_active": True}).sort("created_at", -1)
    mentorships = await cursor.to_list(length=100)
    
    for m in mentorships:
        m.pop("_id", None)
        
    return mentorships




async def accept_challenge_submission(payload) -> dict:
    """Challenge creator accepts a submission, closing the challenge and awarding a badge."""
    challenge = await challenge_collection.find_one({"challenge_id": payload.challenge_id})
    
    if not challenge:
        raise ValueError("Challenge not found.")
    if challenge.get("creator_id") != payload.client_id:
        raise ValueError("Only the user who posted the challenge can select the top submission.")
    if not challenge.get("is_active"):
        raise ValueError("This challenge is already closed.")
        
    submissions = challenge.get("submissions", [])
    if not any(sub["freelancer_id"] == payload.freelancer_id for sub in submissions):
        raise ValueError("This freelancer did not submit to the challenge.")

    await challenge_collection.update_one(
        {"challenge_id": payload.challenge_id},
        {"$set": {
            "is_active": False, 
            "winner_id": payload.freelancer_id
        }}
    )
    
    reward_badge = challenge.get("reward_badge")
    await users_collection.update_one(
        {"user_id": payload.freelancer_id},
        {"$addToSet": {"badges": reward_badge}}
    )
    
    return {
        "message": f"Submission accepted! The '{reward_badge}' badge has been awarded to the freelancer."
    }

async def get_challenges_by_creator(creator_id: str) -> list:
    """Fetches all challenges posted by a specific user (for 'my-created-challenges' page)."""
    await verify_user_exists(creator_id)
    
    cursor = challenge_collection.find({"creator_id": creator_id}).sort("created_at", -1)
    challenges = await cursor.to_list(length=100)
    
    for c in challenges:
        c.pop("_id", None)
        c["submissions"] = sorted(c.get("submissions", []), key=lambda x: x["upvotes"], reverse=True)
        
    return challenges



    
async def select_top_submission(challenge_id: str, creator_id: str, freelancer_id: str) -> dict:
    """Challenge creator marks a specific submission as the 'top candidate'."""
    
    await verify_user_exists(creator_id)
    await verify_user_exists(freelancer_id)

    challenge = await challenge_collection.find_one({"challenge_id": challenge_id})
    if not challenge:
        raise ValueError("Challenge not found.")
        
    if challenge.get("creator_id") != creator_id:
        raise ValueError("Only the creator of this challenge can select the top candidate.")
        
    submissions = challenge.get("submissions", [])
    if not any(sub["freelancer_id"] == freelancer_id for sub in submissions):
        raise ValueError("This freelancer did not submit to the challenge.")

    await challenge_collection.update_one(
        {"challenge_id": challenge_id},
        {"$set": {"top_candidate_id": freelancer_id}}
    )
    
    return {"message": "Top candidate selected successfully."}



    