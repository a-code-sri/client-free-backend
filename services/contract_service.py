from models.schemas import ProjectStatus
from utils.database import contract_collection, proposal_collection, client_request_collection, transaction_collection
from utils.validator import validate_user_exists
import uuid
from datetime import datetime

async def create_contract(proposal_id: str) -> dict:
    """Converts an accepted proposal into an active contract."""
    # 1. Fetch the proposal
    proposal = await proposal_collection.find_one({"proposal_id": proposal_id})
    if not proposal:
        raise ValueError("Proposal not found")

    # 2. Fetch the project to get the client_id
    project = await client_request_collection.find_one({"project_id": proposal["project_id"]})
    if not project:
        raise ValueError("Associated project not found")

    # 3. Create the contract document
    contract_dict = {
        "contract_id": f"cont_{uuid.uuid4().hex[:8]}",
        "proposal_id": proposal_id,
        "project_id": proposal["project_id"],
        "client_id": project["client_id"],
        "freelancer_id": proposal["freelancer_id"],
        "total_amount": proposal["bid_amount"],
        "active_milestones": proposal.get("proposed_milestones", []),
        "status": ProjectStatus.in_progress,
        "started_at": datetime.utcnow()
    }

    await contract_collection.insert_one(contract_dict)
    
    # 4. Update the statuses of the original proposal and project
    await proposal_collection.update_one(
        {"proposal_id": proposal_id}, 
        {"$set": {"status": "Accepted"}}
    )
    await client_request_collection.update_one(
        {"project_id": proposal["project_id"]}, 
        {"$set": {"status": "In Progress"}}
    )

    contract_dict.pop("_id", None)
    return contract_dict


# ==========================================
# NEW: FETCH ACTIVE CONTRACTS
# ==========================================

async def get_active_contracts_for_client(client_id: str) -> list:
    """Fetches all currently active contracts for a specific client."""
    await validate_user_exists(client_id)
    cursor = contract_collection.find({
        "client_id": client_id, 
        "status": ProjectStatus.in_progress
    })
    
    # Assuming you are using Motor (async MongoDB driver)
    contracts = await cursor.to_list(length=100)
    for contract in contracts:
        contract.pop("_id", None)
        
    return contracts

async def get_active_contracts_for_freelancer(freelancer_id: str) -> list:
    """Fetches all currently active contracts for a specific freelancer."""
    await validate_user_exists(freelancer_id)
    cursor = contract_collection.find({
        "freelancer_id": freelancer_id, 
        "status": ProjectStatus.in_progress
    })
    
    contracts = await cursor.to_list(length=100)
    for contract in contracts:
        contract.pop("_id", None)
        
    return contracts


# ==========================================
# UPDATED: PROJECT COMPLETION & FUND RELEASE
# ==========================================

async def complete_contract_and_release_funds(contract_id: str) -> dict:
    """Marks the entire project as complete, takes platform fee, and releases total funds."""
    contract = await contract_collection.find_one({"contract_id": contract_id})
    if not contract:
        raise ValueError("Contract not found")
        
    if contract.get("status") == "Completed" or contract.get("status") == ProjectStatus.completed:
        raise ValueError("Funds have already been released for this contract")

    total_amount = contract.get("total_amount", 0)

    # 1. Sandbox Commission Logic (10% platform cut)
    platform_fee = total_amount * 0.10
    freelancer_earnings = total_amount * 0.90

    # 2. Update the contract document in MongoDB
    await contract_collection.update_one(
        {"contract_id": contract_id},
        {"$set": {
            "status": "Completed", 
            "completed_at": datetime.utcnow()
        }}
    )
    
    # 3. Update the associated project status to Completed
    await client_request_collection.update_one(
        {"project_id": contract["project_id"]}, 
        {"$set": {"status": "Completed"}}
    )

    # 4. Record the earning in the transactions ledger
    transaction_dict = {
        "transaction_id": f"tx_{uuid.uuid4().hex[:8]}",
        "freelancer_id": contract["freelancer_id"],
        "client_id": contract["client_id"],
        "project_id": contract["project_id"],
        "type": "Earning",           
        "amount": freelancer_earnings,
        "status": "Completed",      
        "created_at": datetime.utcnow()
    }
    await transaction_collection.insert_one(transaction_dict)

    # Clean up return object
    contract.pop("_id", None)
    contract["status"] = "Completed"

    return {
        "message": "Project completed successfully. All funds released to Freelancer.",
        "transaction_recorded": {
            "gross_amount": total_amount,
            "platform_fee": platform_fee,
            "net_freelancer_earnings": freelancer_earnings
        },
        "updated_contract": contract
    }