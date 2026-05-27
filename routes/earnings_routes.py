from fastapi import APIRouter, HTTPException
from models.schemas import EarningsDashboardResponse
from services.earnings_service import (
    upgrade_to_pro,
    get_freelancer_earnings_dashboard
)

router = APIRouter()

@router.post("/sandbox/subscribe-pro/{user_id}")
async def subscribe_pro_endpoint(user_id: str):
    """
    Sandbox Action: Freelancer buys the Pro subscription.
    Simulates a checkout that upgrades their profile status.
    """
    try:
        result = await upgrade_to_pro(user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{freelancer_id}/dashboard", response_model=EarningsDashboardResponse)
async def fetch_earnings_dashboard_endpoint(freelancer_id: str):
    """
    Frontend Action: Loads the Earnings page.
    Returns the total earned, total commission paid, pending payments, 
    and withdrawal history table data.
    """
    try:
        dashboard_data = await get_freelancer_earnings_dashboard(freelancer_id)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))