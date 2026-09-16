import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db import engine
from app.models.profile import Profile, ProfileSkill
from app.models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        skills = session.exec(select(ProfileSkill).where(ProfileSkill.user_id == user.id)).all()
        profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()

    return {
        "skills": [{"name": s.name, "category": s.category, "source": s.source} for s in skills],
        "experience": json.loads(profile.experience_json) if profile else [],
        "projects": json.loads(profile.projects_json) if profile else [],
        "education": json.loads(profile.education_json) if profile else [],
    }
