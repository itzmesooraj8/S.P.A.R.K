from fastapi import APIRouter

router = APIRouter(tags=["Weather"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Weather"}
