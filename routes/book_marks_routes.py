from fastapi import APIRouter, HTTPException
from models.schemas import BookMark
from services.book_marks_service import add_bookmark, remove_bookmark, get_bookmarked_freelancers

router = APIRouter()

@router.post("/add")
async def add_bookmark_endpoint(payload: BookMark):
    """Frontend Action: Client saves one or more freelancers."""
    try:
        result = await add_bookmark(payload.client_id, payload.freelancers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remove")
async def remove_bookmark_endpoint(payload: BookMark):
    """Frontend Action: Client removes one or more freelancers."""
    try:
        result = await remove_bookmark(payload.client_id, payload.freelancers)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}/list")
async def list_bookmarks_endpoint(client_id: str):
    """Returns the full portfolio objects of saved freelancers."""
    try:
        freelancers = await get_bookmarked_freelancers(client_id)
        return {"client_id": client_id, "saved_freelancers": freelancers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))