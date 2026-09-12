import base64

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.compile_client import compile_tex
from app.db import engine
from app.models.job_application import JobApplication

router = APIRouter(prefix="/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    title: str = "Untitled"
    tex_source: str


class JobResponse(BaseModel):
    id: int
    title: str
    tex_source: str


class ResumeResponse(BaseModel):
    tex_source: str


class SaveResumeRequest(BaseModel):
    tex_source: str


class CompileRequest(BaseModel):
    tex_source: str


class CompileResponse(BaseModel):
    status: str
    pdf_base64: str | None
    log: str
    message: str | None


def _get_job_or_404(session: Session, job_id: int) -> JobApplication:
    job = session.get(JobApplication, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobResponse)
def create_job(payload: CreateJobRequest) -> JobResponse:
    with Session(engine) as session:
        job = JobApplication(title=payload.title, tex_source=payload.tex_source)
        session.add(job)
        session.commit()
        session.refresh(job)
        return JobResponse(id=job.id, title=job.title, tex_source=job.tex_source)


@router.get("", response_model=list[JobResponse])
def list_jobs() -> list[JobResponse]:
    with Session(engine) as session:
        jobs = session.exec(select(JobApplication)).all()
        return [JobResponse(id=j.id, title=j.title, tex_source=j.tex_source) for j in jobs]


@router.get("/{job_id}/resume", response_model=ResumeResponse)
def get_resume(job_id: int) -> ResumeResponse:
    with Session(engine) as session:
        job = _get_job_or_404(session, job_id)
        return ResumeResponse(tex_source=job.tex_source)


@router.put("/{job_id}/resume")
def save_resume(job_id: int, payload: SaveResumeRequest) -> dict:
    with Session(engine) as session:
        job = _get_job_or_404(session, job_id)
        job.tex_source = payload.tex_source
        session.add(job)
        session.commit()
        return {"status": "saved"}


@router.post("/{job_id}/compile", response_model=CompileResponse)
async def compile_job(job_id: int, payload: CompileRequest) -> CompileResponse:
    with Session(engine) as session:
        job = _get_job_or_404(session, job_id)
        job.tex_source = payload.tex_source
        session.add(job)
        session.commit()

    result = await compile_tex(payload.tex_source, job_id=str(job_id))

    pdf_base64 = base64.b64encode(result.pdf_bytes).decode("ascii") if result.pdf_bytes else None
    return CompileResponse(status=result.status, pdf_base64=pdf_base64, log=result.log, message=result.message)
