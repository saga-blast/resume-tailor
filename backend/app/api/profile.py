import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db import engine
from app.models.profile import Profile, ProfileSkill
from app.models.user import User

router = APIRouter(prefix="/profile", tags=["profile"])


class AddSkillRequest(BaseModel):
    name: str
    category: str = "skill"


class AddProjectRequest(BaseModel):
    name: str
    description: str = ""


def _get_or_create_profile(session: Session, user_id: int) -> Profile:
    profile = session.exec(select(Profile).where(Profile.user_id == user_id)).first()
    if not profile:
        profile = Profile(user_id=user_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


@router.get("")
def get_profile(user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        skills = session.exec(select(ProfileSkill).where(ProfileSkill.user_id == user.id)).all()
        profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()

    return {
        "skills": [{"id": s.id, "name": s.name, "category": s.category, "source": s.source} for s in skills],
        "experience": json.loads(profile.experience_json) if profile else [],
        "projects": json.loads(profile.projects_json) if profile else [],
        "education": json.loads(profile.education_json) if profile else [],
    }


@router.post("/skills")
def add_skill(payload: AddSkillRequest, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        skill = ProfileSkill(
            user_id=user.id, name=payload.name, category=payload.category, source="manual"
        )
        session.add(skill)
        session.commit()
        session.refresh(skill)
        return {"id": skill.id, "name": skill.name, "category": skill.category, "source": skill.source}


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        skill = session.get(ProfileSkill, skill_id)
        if not skill or skill.user_id != user.id:
            raise HTTPException(status_code=404, detail="Skill not found")
        session.delete(skill)
        session.commit()
        return {"status": "deleted"}


@router.post("/projects")
def add_project(payload: AddProjectRequest, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        profile = _get_or_create_profile(session, user.id)
        projects = json.loads(profile.projects_json)
        projects.append({"name": payload.name, "description": payload.description})
        profile.projects_json = json.dumps(projects)
        session.add(profile)
        session.commit()
        return {"projects": projects}


@router.delete("/projects/{index}")
def delete_project(index: int, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        projects = json.loads(profile.projects_json)
        if index < 0 or index >= len(projects):
            raise HTTPException(status_code=404, detail="Project not found")
        projects.pop(index)
        profile.projects_json = json.dumps(projects)
        session.add(profile)
        session.commit()
        return {"projects": projects}
