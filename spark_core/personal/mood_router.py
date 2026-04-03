from fastapi import APIRouter

router = APIRouter(tags=["Mood"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Mood"}
