from fastapi import APIRouter

router = APIRouter(tags=["Search"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Search"}
