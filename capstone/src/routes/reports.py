from fastapi import APIRouter, Depends

from ..auth import verify_token
from ..reports import build_weekly_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/weekly", status_code=201)
def weekly_report(user: dict = Depends(verify_token)):
    result = build_weekly_report(user["id"], user["email"])
    return {"trigger": "manual", **result}
