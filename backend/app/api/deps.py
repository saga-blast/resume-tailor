from fastapi import Cookie, HTTPException
from sqlmodel import Session

from app.db import engine
from app.models.user import User
from app.security import COOKIE_NAME, decode_access_token


def get_current_user(
    resume_tailor_session: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> User:
    if not resume_tailor_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_access_token(resume_tailor_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    with Session(engine) as session:
        user = session.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
