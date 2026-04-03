from fastapi import APIRouter

router = APIRouter(tags=["Task"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Task"}
