from fastapi import APIRouter, Request
from backend.auth import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def admin_health_check(request: Request):
    # This proves admin routing + auth works
    require_admin(request)
    return {"status": "admin ok"}
