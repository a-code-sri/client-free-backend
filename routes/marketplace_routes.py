from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import ClientRequest, Proposal
from services.marketplace_service import (
    create_client_request, 
    create_proposal,
    get_all_client_requests,
    get_proposals_by_project
)
router = APIRouter()

@router.post("/requests", response_model=ClientRequest)
async def post_client_request(request: ClientRequest):
    try:
        new_request = await create_client_request(request)
        return new_request
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposals", response_model=Proposal)
async def post_proposal(proposal: Proposal):
    try:
        new_proposal = await create_proposal(proposal)
        return new_proposal
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/requests", response_model=List[ClientRequest])
async def fetch_open_requests():
    """Used by Freelancers to browse available jobs."""
    try:
        requests = await get_all_client_requests()
        return requests
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/requests/{project_id}/proposals", response_model=List[Proposal])
async def fetch_project_proposals(project_id: str):
    """Used by Clients to view bids on their specific project."""
    try:
        proposals = await get_proposals_by_project(project_id)
        return proposals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))