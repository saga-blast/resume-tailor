import base64
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.compile_client import compile_tex
from app.db import engine
from app.llm.factory import LLMNotConfiguredError, get_llm_provider
from app.llm.prompts import extract_requirements
from app.llm.schemas import ExtractedRequirements
from app.models.job_application import JobApplication
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    title: str = "Untitled"
    company: str | None = None
    tex_source: str = ""
    jd_text: str | None = None


class JobResponse(BaseModel):
    id: int
    title: str
    company: str | None
    tex_source: str
    jd_raw_text: str | None
    extracted_requirements: list[dict] | None
    match_percentage: float | None
    status: str


class SaveResumeRequest(BaseModel):
    tex_source: str


class CompileRequest(BaseModel):
    tex_source: str


class CompileResponse(BaseModel):
    status: str
    pdf_base64: str | None
    log: str
    message: str | None


def _to_response(job: JobApplication) -> JobResponse:
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        tex_source=job.tex_source,
        jd_raw_text=job.jd_raw_text,
        extracted_requirements=(
            json.loads(job.extracted_requirements_json) if job.extracted_requirements_json else None
        ),
        match_percentage=job.match_percentage,
        status=job.status,
    )


def _get_owned_job_or_404(session: Session, job_id: int, user_id: int) -> JobApplication:
    job = session.get(JobApplication, job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobResponse)
async def create_job(payload: CreateJobRequest, user: User = Depends(get_current_user)) -> JobResponse:
    with Session(engine) as session:
        job = JobApplication(
            user_id=user.id,
            title=payload.title,
            company=payload.company,
            tex_source=payload.tex_source,
            jd_raw_text=payload.jd_text,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.id

        provider = None
        if payload.jd_text:
            try:
                provider = get_llm_provider(session, user.id)
            except LLMNotConfiguredError as exc:
                session.delete(job)
                session.commit()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Configure an LLM provider (POST /onboarding/llm-config) before "
                        "submitting a job description."
                    ),
                ) from exc

    if payload.jd_text and provider is not None:
        try:
            extracted = await provider.extract_structured(
                system_prompt=extract_requirements.SYSTEM_PROMPT,
                user_prompt=extract_requirements.build_user_prompt(payload.jd_text),
                schema=ExtractedRequirements,
                tool_name=extract_requirements.TOOL_NAME,
                tool_description=extract_requirements.TOOL_DESCRIPTION,
            )
        except Exception as exc:
            with Session(engine) as session:
                job = session.get(JobApplication, job_id)
                job.status = "extraction_failed"
                session.add(job)
                session.commit()
            raise HTTPException(status_code=502, detail=f"Requirement extraction failed: {exc}") from exc

        with Session(engine) as session:
            job = session.get(JobApplication, job_id)
            job.extracted_requirements_json = json.dumps([r.model_dump() for r in extracted.requirements])
            job.status = "requirements_extracted"
            session.add(job)
            session.commit()
            session.refresh(job)
            return _to_response(job)

    with Session(engine) as session:
        job = session.get(JobApplication, job_id)
        return _to_response(job)


@router.get("", response_model=list[JobResponse])
def list_jobs(user: User = Depends(get_current_user)) -> list[JobResponse]:
    with Session(engine) as session:
        jobs = session.exec(select(JobApplication).where(JobApplication.user_id == user.id)).all()
        return [_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, user: User = Depends(get_current_user)) -> JobResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        return _to_response(job)


@router.get("/{job_id}/resume", response_model=SaveResumeRequest)
def get_resume(job_id: int, user: User = Depends(get_current_user)) -> SaveResumeRequest:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        return SaveResumeRequest(tex_source=job.tex_source)


@router.put("/{job_id}/resume")
def save_resume(job_id: int, payload: SaveResumeRequest, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        job.tex_source = payload.tex_source
        session.add(job)
        session.commit()
        return {"status": "saved"}


@router.post("/{job_id}/compile", response_model=CompileResponse)
async def compile_job(
    job_id: int, payload: CompileRequest, user: User = Depends(get_current_user)
) -> CompileResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        job.tex_source = payload.tex_source
        session.add(job)
        session.commit()

    result = await compile_tex(payload.tex_source, job_id=str(job_id))

    pdf_base64 = base64.b64encode(result.pdf_bytes).decode("ascii") if result.pdf_bytes else None
    return CompileResponse(status=result.status, pdf_base64=pdf_base64, log=result.log, message=result.message)
