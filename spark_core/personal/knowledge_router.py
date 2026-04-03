from fastapi import APIRouter

router = APIRouter(tags=["Knowledge"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Knowledge"}
