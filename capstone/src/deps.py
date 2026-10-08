from fastapi import Depends

from .auth import verify_token


def get_user_id(user: dict = Depends(verify_token)) -> str:
    return user["id"]
