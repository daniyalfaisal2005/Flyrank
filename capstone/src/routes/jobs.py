from fastapi import APIRouter, Depends

from ..auth import verify_token
from ..checker import run_check_cycle

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run-now")
def run_now(user: dict = Depends(verify_token)):
    summary = run_check_cycle()
    return {"trigger": "manual", "user": user["email"], **summary}
