from fastapi import APIRouter

router = APIRouter(tags=["Voice_clone"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Voice_clone"}
