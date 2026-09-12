from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine
from app.models.user import User
from app.security import hash_password

settings = get_settings()


def ensure_seed_user() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == settings.seed_user_email)).first()
        if existing:
            return
        user = User(
            email=settings.seed_user_email,
            hashed_password=hash_password(settings.seed_user_password),
        )
        session.add(user)
        session.commit()
