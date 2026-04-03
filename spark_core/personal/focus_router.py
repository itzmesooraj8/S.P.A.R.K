from fastapi import APIRouter

router = APIRouter(tags=["Focus"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Focus"}
