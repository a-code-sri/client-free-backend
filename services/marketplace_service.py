from models.schemas import ClientRequest, Proposal
from utils.database import client_request_collection, proposal_collection
import uuid
from datetime import datetime,timezone
from fastapi import HTTPException

from fastapi import HTTPException
from utils.database import client_request_collection, proposal_collection

async def validate_project_exists(project_id: str) -> dict:
    """Fetches a project or throws a 404 if it doesn't exist."""
    if not project_id:
        raise HTTPException(status_code=400, detail="Project ID is required.")
        
    project = await client_request_collection.find_one({"project_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID '{project_id}' does not exist.")
    return project

async def validate_project_is_unique(project_id: str) -> None:
    """Throws a 409 Conflict if the project ID is already taken."""
    if project_id and project_id not in ["string", ""]:
        project_exists = await client_request_collection.find_one({"project_id": project_id})
        if project_exists:
            raise HTTPException(status_code=409, detail=f"Project ID '{project_id}' already exists.")
        
from models.schemas import ClientRequest, Proposal
from utils.database import client_request_collection, proposal_collection
import uuid
from datetime import datetime, timezone

async def create_client_request(request_data: ClientRequest) -> dict:
    request_dict = request_data.model_dump(mode='json')
    project_id = request_dict.get("project_id")
    
    # 1. MODULAR CHECK: Throw HTTP error immediately if ID is taken
    await validate_project_is_unique(project_id)
    
    if project_id in [None, "string", ""]:
        request_dict["project_id"] = f"proj_{uuid.uuid4().hex[:8]}"
        
    request_dict["created_at"] = datetime.now(timezone.utc)
    
    await client_request_collection.insert_one(request_dict)
    request_dict.pop("_id", None)
    
    return request_dict


async def create_proposal(proposal_data: Proposal) -> dict:
    proposal_dict = proposal_data.model_dump(mode='json')
    project_id = proposal_dict.get("project_id")
    freelancer_id = proposal_dict.get("freelancer_id")
    proposal_id = proposal_dict.get("proposal_id")
    
    # 1. MODULAR CHECK: Validates project exists and returns it, or throws 404
    project = await validate_project_exists(project_id)
    
    # 2. Status Check
    project_status = project.get("status", "Open")
    if project_status not in ["Open", "Pending"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot submit proposal. Project is currently '{project_status}'."
        )

    # 3. Check if we have an existing proposal
    existing_proposal = None
    if proposal_id not in [None, "string", ""]:
        existing_proposal = await proposal_collection.find_one({"proposal_id": proposal_id})
    else:
        existing_proposal = await proposal_collection.find_one({
            "project_id": project_id,
            "freelancer_id": freelancer_id
        })

    # 4. Handle existing proposal logic
    if existing_proposal:
        if existing_proposal.get("freelancer_id") == freelancer_id:
            proposal_dict["proposal_id"] = existing_proposal["proposal_id"]
            proposal_dict["created_at"] = existing_proposal.get("created_at", datetime.now(timezone.utc))
            
            await proposal_collection.update_one(
                {"proposal_id": existing_proposal["proposal_id"]},
                {"$set": proposal_dict}
            )
            
            proposal_dict.pop("_id", None)
            proposal_dict["status"] = "proposal_updated" 
            return proposal_dict
        else:
            raise HTTPException(status_code=403, detail="Proposal ID belongs to another freelancer.")

    # 5. Brand new proposal
    proposal_dict["proposal_id"] = f"prop_{uuid.uuid4().hex[:8]}"
    proposal_dict["created_at"] = datetime.now(timezone.utc)
    
    await proposal_collection.insert_one(proposal_dict)
    proposal_dict.pop("_id", None)
    
    return proposal_dict


async def get_all_client_requests() -> list:
    cursor = client_request_collection.find({"status": "Open"}).sort("created_at", -1)
    requests = await cursor.to_list(length=100)
    
    for req in requests:
        req.pop("_id", None)
    return requests


async def get_proposals_by_project(project_id: str) -> list:
    # 1. MODULAR CHECK: Validate project exists or throw 404
    await validate_project_exists(project_id)
    
    cursor = proposal_collection.find({"project_id": project_id}).sort("created_at", -1)
    proposals = await cursor.to_list(length=100)
    
    for prop in proposals:
        prop.pop("_id", None)
    return proposals