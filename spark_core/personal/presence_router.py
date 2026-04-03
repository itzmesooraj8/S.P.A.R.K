from fastapi import APIRouter

router = APIRouter(tags=["Presence"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Presence"}
