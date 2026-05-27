from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import TopCandidatePayload
from services.community_service import select_top_submission

from models.schemas import (
    FeedPostCreate, 
    MentorshipOffer, 
    ChallengeCreate, 
    ChallengeSubmissionPayload,
    FeedPostResponse,
    MentorshipSessionResponse,
    UserMentorshipDashboard,
    ChallengeResponse,
    GenericMessageResponse,
    AcceptSubmissionPayload
)
from utils.validator import validate_user_exists
from services.community_service import (
    create_feed_post, 
    get_public_feed, 
    create_mentorship_offer, 
    book_mentorship_session,
    toggle_like_post,
    create_weekly_challenge, 
    submit_to_challenge, 
    upvote_submission, 
    get_active_challenges,
    get_user_mentorship_details,
    get_user_posts,
    get_active_methorships,
    accept_challenge_submission
)

router = APIRouter()
@router.post("/feed", response_model=FeedPostResponse)
async def add_post(payload: FeedPostCreate):
    try:
        post = await create_feed_post(payload)
        return post
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feed", response_model=List[FeedPostResponse])
async def view_feed(limit: int = 50):
    try:
        return await get_public_feed(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feed/{post_id}/like", response_model=GenericMessageResponse)
async def toggle_post_like(post_id: str, user_id: str):
    """
    Frontend Action: User clicks the 'Heart' icon on a feed post.
    Automatically handles liking and un-liking.
    """
    try:
        result = await toggle_like_post(post_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mentorship", response_model=MentorshipSessionResponse)
async def offer_mentorship(payload: MentorshipOffer):
    try:
        session = await create_mentorship_offer(payload)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mentorship/{session_id}/book", response_model=GenericMessageResponse)
async def book_mentorship(session_id: str, mentee_id: str):
    try:
        result = await book_mentorship_session(session_id, mentee_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mentorship/user/{user_id}", response_model=UserMentorshipDashboard)
async def get_user_mentorship_dashboard(user_id: str):
    """Returns all mentorship sessions a user has offered, and all sessions they have booked."""
    try:
        return await get_user_mentorship_details(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/challenges", response_model=ChallengeResponse)
async def create_challenge(payload: ChallengeCreate):
    """Admin endpoint to post a new weekly challenge."""
    try:
        challenge = await create_weekly_challenge(payload)
        return challenge
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/challenges/active", response_model=List[ChallengeResponse])
async def view_active_challenges():
    """Frontend Action: Users view the challenges page and top submissions."""
    try:
        return await get_active_challenges()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/challenges/submit", response_model=GenericMessageResponse)
async def submit_challenge_project(payload: ChallengeSubmissionPayload):
    """Frontend Action: Freelancer uploads their Figma/GitHub link."""
    try:
        result = await submit_to_challenge(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/challenges/{challenge_id}/upvote/{freelancer_id}", response_model=GenericMessageResponse)
async def vote_for_submission(challenge_id: str, freelancer_id: str):
    """Frontend Action: User clicks the 'Upvote' arrow on a submission."""
    try:
        result = await upvote_submission(challenge_id, freelancer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/feed/{user_id}", response_model=List[FeedPostResponse])
async def view_feed(user_id):
    await validate_user_exists(user_id)
    try:
        return await get_user_posts(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mentorship/active")
async def get_mentorships():
    try:
        return await get_active_methorships()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/challenges/accept", response_model=GenericMessageResponse)
async def accept_submission(payload: AcceptSubmissionPayload):
    """Frontend Action: Creator selects the top submission, awarding the badge."""
    try:
        result = await accept_challenge_submission(payload)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/challenges/top-candidate", response_model=GenericMessageResponse)
async def mark_top_candidate(payload: TopCandidatePayload):
    """Frontend Action: Creator highlights a top submission for an active challenge."""
    try:
        result = await select_top_submission(
            challenge_id=payload.challenge_id,
            creator_id=payload.creator_id,
            freelancer_id=payload.freelancer_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))