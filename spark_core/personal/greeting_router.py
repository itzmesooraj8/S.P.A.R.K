from fastapi import APIRouter

router = APIRouter(tags=["Greeting"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "Greeting"}
