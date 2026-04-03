from fastapi import APIRouter

router = APIRouter(tags=["App"])

@router.get("/status")
async def get_status():
    return {"status": "ok", "module": "App"}
