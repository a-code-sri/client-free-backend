from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from services.contract_service import (
    create_contract, 
    complete_contract_and_release_funds,
    get_active_contracts_for_client,
    get_active_contracts_for_freelancer
)

router = APIRouter()

@router.post("/accept-proposal/{proposal_id}")
async def accept_proposal_endpoint(proposal_id: str):
    """
    Frontend Action: Client clicks 'Accept Bid'.
    Converts a proposal into a live contract and locks the job.
    """
    try:
        contract = await create_contract(proposal_id)
        return contract
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{contract_id}/complete")
async def complete_contract_endpoint(contract_id: str):
    """
    Frontend Action: Client clicks 'Complete Project & Release Funds'.
    Releases the total funds to the freelancer minus the 10% platform fee.
    """
    try:
        result = await complete_contract_and_release_funds(contract_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/client/{client_id}/active")
async def fetch_client_active_contracts(client_id: str):
    """
    Frontend Action: Loads the Client Dashboard.
    Fetches all in-progress contracts for this client.
    """
    try:
        contracts = await get_active_contracts_for_client(client_id)
        return {"active_contracts": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/freelancer/{freelancer_id}/active")
async def fetch_freelancer_active_contracts(freelancer_id: str):
    """
    Frontend Action: Loads the Freelancer Workspace.
    Fetches all in-progress contracts for this freelancer.
    """
    try:
        contracts = await get_active_contracts_for_freelancer(freelancer_id)
        return {"active_contracts": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

