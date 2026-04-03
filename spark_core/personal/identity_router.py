from fastapi import APIRouter

router = APIRouter(tags=["Identity"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Identity"}
