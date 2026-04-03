from fastapi import APIRouter

router = APIRouter(tags=["Notes"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Notes"}
