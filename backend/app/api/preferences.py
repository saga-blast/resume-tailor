from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db import engine
from app.models.preference_memory import PreferenceMemory
from app.models.user import User

router = APIRouter(prefix="/preferences", tags=["preferences"])


class PreferenceResponse(BaseModel):
    id: int
    fact_text: str
    status: str
    question_text: str
    answer_text: str


class UpdatePreferenceRequest(BaseModel):
    status: str  # "confirmed" | "declined"


def _to_response(p: PreferenceMemory) -> PreferenceResponse:
    return PreferenceResponse(
        id=p.id,
        fact_text=p.fact_text,
        status=p.status,
        question_text=p.question_text,
        answer_text=p.answer_text,
    )


@router.get("", response_model=list[PreferenceResponse])
def list_preferences(user: User = Depends(get_current_user)) -> list[PreferenceResponse]:
    with Session(engine) as session:
        prefs = session.exec(
            select(PreferenceMemory).where(PreferenceMemory.user_id == user.id)
        ).all()
        return [_to_response(p) for p in prefs]


@router.patch("/{pref_id}", response_model=PreferenceResponse)
def update_preference(
    pref_id: int, payload: UpdatePreferenceRequest, user: User = Depends(get_current_user)
) -> PreferenceResponse:
    with Session(engine) as session:
        pref = session.get(PreferenceMemory, pref_id)
        if not pref or pref.user_id != user.id:
            raise HTTPException(status_code=404, detail="Preference not found")
        pref.status = payload.status
        pref.updated_at = datetime.now(timezone.utc)
        session.add(pref)
        session.commit()
        session.refresh(pref)
        return _to_response(pref)


@router.delete("/{pref_id}")
def delete_preference(pref_id: int, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        pref = session.get(PreferenceMemory, pref_id)
        if not pref or pref.user_id != user.id:
            raise HTTPException(status_code=404, detail="Preference not found")
        session.delete(pref)
        session.commit()
        return {"status": "deleted"}
