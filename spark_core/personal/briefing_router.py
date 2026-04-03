from fastapi import APIRouter

router = APIRouter(tags=["Briefing"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Briefing"}
