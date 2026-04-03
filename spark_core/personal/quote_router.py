from fastapi import APIRouter

router = APIRouter(tags=["Quote"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Quote"}
