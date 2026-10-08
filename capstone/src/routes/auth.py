from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..auth import supabase_client

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=6, max_length=128)


def _check_credentials(body: Credentials) -> None:
    if "@" not in body.email:
        raise HTTPException(status_code=400, detail="email must be a valid address")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")


@router.post("/signup", status_code=201)
def signup(body: Credentials):
    _check_credentials(body)
    try:
        result = supabase_client.auth.sign_up({"email": body.email, "password": body.password})
        user = result.user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if user is None:
        raise HTTPException(status_code=400, detail="signup failed")
    return {"user": {"id": user.id, "email": user.email}}


@router.post("/login")
def login(body: Credentials):
    try:
        result = supabase_client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        session = result.session
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {"access_token": session.access_token, "refresh_token": session.refresh_token}
