import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.crypto import decrypt_secret, encrypt_secret
from app.db import engine
from app.llm.factory import LLMNotConfiguredError, build_provider, get_llm_provider
from app.llm.prompts import parse_resume
from app.llm.schemas import ParsedProfile
from app.models.llm_config import LLMProviderConfig
from app.models.profile import Profile, ProfileSkill
from app.models.resume import ResumeTemplate
from app.models.user import User

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class LLMConfigRequest(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-5"
    api_key: str


class OnboardingStatus(BaseModel):
    has_llm_config: bool
    has_template: bool
    has_profile: bool


class AvailableModelsResponse(BaseModel):
    models: list[str]


class UpdateModelRequest(BaseModel):
    model: str


@router.get("/status", response_model=OnboardingStatus)
def get_status(user: User = Depends(get_current_user)) -> OnboardingStatus:
    with Session(engine) as session:
        has_llm = (
            session.exec(
                select(LLMProviderConfig).where(
                    LLMProviderConfig.user_id == user.id,
                    LLMProviderConfig.is_active.is_(True),
                )
            ).first()
            is not None
        )
        has_template = (
            session.exec(select(ResumeTemplate).where(ResumeTemplate.user_id == user.id)).first()
            is not None
        )
        # A ResumeTemplate row only means a file was uploaded -- it's written before
        # parsing is attempted, so it stays true even if parsing then fails. Whether
        # onboarding is actually *complete* depends on a Profile having been written,
        # which only happens after a successful parse.
        has_profile = (
            session.exec(select(Profile).where(Profile.user_id == user.id)).first() is not None
        )
    return OnboardingStatus(has_llm_config=has_llm, has_template=has_template, has_profile=has_profile)


@router.post("/llm-config")
def save_llm_config(payload: LLMConfigRequest, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        existing = session.exec(
            select(LLMProviderConfig).where(LLMProviderConfig.user_id == user.id)
        ).first()
        encrypted = encrypt_secret(payload.api_key)
        if existing:
            existing.provider = payload.provider
            existing.model = payload.model
            existing.encrypted_api_key = encrypted
            existing.is_active = True
            session.add(existing)
        else:
            session.add(
                LLMProviderConfig(
                    user_id=user.id,
                    provider=payload.provider,
                    model=payload.model,
                    encrypted_api_key=encrypted,
                )
            )
        session.commit()
    return {"status": "saved"}


@router.get("/available-models", response_model=AvailableModelsResponse)
async def available_models(user: User = Depends(get_current_user)) -> AvailableModelsResponse:
    """Model lineups shift over time (we've now hit a stale hardcoded default twice) --
    ask the provider directly what this key can actually use instead of guessing."""
    with Session(engine) as session:
        try:
            provider = get_llm_provider(session, user.id)
        except LLMNotConfiguredError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        models = await provider.list_models()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list models: {exc}") from exc

    return AvailableModelsResponse(models=sorted(models))


class PingSchema(BaseModel):
    ok: bool


@router.post("/verify-model")
async def verify_model(payload: UpdateModelRequest, user: User = Depends(get_current_user)) -> dict:
    """A model can exist and still not support the tool-calling this app relies on
    (a real, distinct failure mode from a bad model ID -- e.g. some Groq-hosted
    models reject tool definitions outright). Run an actual minimal tool call
    before letting the user commit to a model and spend a slow resume upload
    finding out it doesn't work."""
    with Session(engine) as session:
        config = session.exec(
            select(LLMProviderConfig).where(LLMProviderConfig.user_id == user.id)
        ).first()
        if not config:
            raise HTTPException(status_code=400, detail="No LLM provider configured yet")
        api_key = decrypt_secret(config.encrypted_api_key)
        provider = build_provider(config.provider, api_key, payload.model)

    try:
        result = await provider.extract_structured(
            system_prompt="You are a test harness verifying tool-calling support.",
            user_prompt="Call the ping tool with ok set to true.",
            schema=PingSchema,
            tool_name="ping",
            tool_description="Respond with ok=true to confirm tool calling works.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"This model doesn't support tool calling here: {exc}"
        ) from exc

    if not result.ok:
        raise HTTPException(
            status_code=400, detail="Model responded but not as expected -- try a different model."
        )

    return {"status": "verified"}


@router.patch("/llm-config/model")
def update_model(payload: UpdateModelRequest, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        config = session.exec(
            select(LLMProviderConfig).where(LLMProviderConfig.user_id == user.id)
        ).first()
        if not config:
            raise HTTPException(status_code=400, detail="No LLM provider configured yet")
        config.model = payload.model
        session.add(config)
        session.commit()
    return {"status": "saved"}


@router.post("/template")
async def upload_template(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
) -> dict:
    raw_bytes = await file.read()
    raw_tex = raw_bytes.decode("utf-8", errors="replace")

    with Session(engine) as session:
        session.add(ResumeTemplate(user_id=user.id, raw_tex=raw_tex))
        session.commit()

        try:
            provider = get_llm_provider(session, user.id)
        except LLMNotConfiguredError as exc:
            raise HTTPException(
                status_code=400,
                detail="Configure an LLM provider (POST /onboarding/llm-config) before uploading a template.",
            ) from exc

    try:
        parsed = await provider.extract_structured(
            system_prompt=parse_resume.SYSTEM_PROMPT,
            user_prompt=parse_resume.build_user_prompt(raw_tex),
            schema=ParsedProfile,
            tool_name=parse_resume.TOOL_NAME,
            tool_description=parse_resume.TOOL_DESCRIPTION,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Resume parsing failed: {exc}") from exc

    with Session(engine) as session:
        old_skills = session.exec(select(ProfileSkill).where(ProfileSkill.user_id == user.id)).all()
        for skill in old_skills:
            session.delete(skill)
        for skill in parsed.skills:
            session.add(
                ProfileSkill(user_id=user.id, name=skill.name, category=skill.category, source="resume")
            )

        profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()
        experience_json = json.dumps([e.model_dump() for e in parsed.experience])
        projects_json = json.dumps([p.model_dump() for p in parsed.projects])
        education_json = json.dumps([e.model_dump() for e in parsed.education])
        if profile:
            profile.experience_json = experience_json
            profile.projects_json = projects_json
            profile.education_json = education_json
        else:
            profile = Profile(
                user_id=user.id,
                experience_json=experience_json,
                projects_json=projects_json,
                education_json=education_json,
            )
        session.add(profile)
        session.commit()

    return {"status": "parsed", "profile": parsed.model_dump()}
