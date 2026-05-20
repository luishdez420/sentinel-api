from fastapi import APIRouter
from app.core.metrics import snapshot

router = APIRouter(prefix="/metrics", tags=["ops"])

@router.get("")
def get_metrics():
    return snapshot()