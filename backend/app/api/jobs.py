import asyncio
import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.compile_client import compile_tex
from app.db import engine
from app.llm.factory import LLMNotConfiguredError, get_llm_provider
from app.llm.prompts import extract_requirements, match_requirements, rewrite_content
from app.llm.schemas import ContentRewritePlan, ExtractedRequirements, MatchSuggestions, TrimPlan
from app.models.job_application import JobApplication, RequirementMatch
from app.models.preference_memory import PreferenceMemory
from app.models.profile import Profile, ProfileSkill
from app.models.resume import ResumeTemplate
from app.models.user import User
from app.preference_utils import normalize_key
from app.resume_generation import (
    apply_text_rewrites,
    count_pdf_pages,
    extract_bullets,
    extract_summary,
    filter_safe_trim_indices,
    generate_tailored_resume,
    remove_bullets,
    resolve_highlight_term,
)

MAX_TRIM_ITERATIONS = 4

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


class RequirementMatchResponse(BaseModel):
    id: int
    requirement_text: str
    requirement_category: str
    priority: str
    match_status: str
    matched_skill_name: str | None
    clarifying_question: str | None
    user_answer: str | None


class MatchSummaryResponse(BaseModel):
    match_percentage: float
    matches: list[RequirementMatchResponse]


class AnswerQuestionRequest(BaseModel):
    confirmed: bool


class GenerateResumeResponse(BaseModel):
    tex_source: str
    skills_added: list[str]
    keywords_highlighted: list[str]
    bullets_rewritten: int
    bullets_trimmed: int
    final_page_count: int | None
    warning: str | None


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


def _match_to_response(m: RequirementMatch) -> RequirementMatchResponse:
    return RequirementMatchResponse(
        id=m.id,
        requirement_text=m.requirement_text,
        requirement_category=m.requirement_category,
        priority=m.priority,
        match_status=m.match_status,
        matched_skill_name=m.matched_skill_name,
        clarifying_question=m.clarifying_question,
        user_answer=m.user_answer,
    )


def _compute_match_percentage(matches: list[RequirementMatch]) -> float:
    if not matches:
        return 0.0
    matched = sum(1 for m in matches if m.match_status == "matched")
    return round((matched / len(matches)) * 100, 1)


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


@router.delete("/{job_id}")
def delete_job(job_id: int, user: User = Depends(get_current_user)) -> dict:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        matches = session.exec(
            select(RequirementMatch).where(RequirementMatch.job_application_id == job_id)
        ).all()
        for m in matches:
            session.delete(m)
        session.delete(job)
        session.commit()
        return {"status": "deleted"}


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


@router.post("/{job_id}/match", response_model=MatchSummaryResponse)
async def match_job(job_id: int, user: User = Depends(get_current_user)) -> MatchSummaryResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        if not job.extracted_requirements_json:
            raise HTTPException(
                status_code=400, detail="Extract requirements for this job before matching (submit a JD first)."
            )
        requirements = json.loads(job.extracted_requirements_json)

        skills = session.exec(select(ProfileSkill).where(ProfileSkill.user_id == user.id)).all()
        skills_payload = [{"name": s.name, "category": s.category} for s in skills]

        profile = session.exec(select(Profile).where(Profile.user_id == user.id)).first()
        experience_payload = json.loads(profile.experience_json) if profile else []
        education_payload = json.loads(profile.education_json) if profile else []
        projects_payload = json.loads(profile.projects_json) if profile else []

        preferences = session.exec(select(PreferenceMemory).where(PreferenceMemory.user_id == user.id)).all()
        preferences_payload = [{"fact": p.fact_text, "status": p.status} for p in preferences]
        preferences_by_key = {p.normalized_key: p for p in preferences}

        try:
            provider = get_llm_provider(session, user.id)
        except LLMNotConfiguredError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        suggestions = await provider.extract_structured(
            system_prompt=match_requirements.SYSTEM_PROMPT,
            user_prompt=match_requirements.build_user_prompt(
                requirements,
                skills_payload,
                experience_payload,
                education_payload,
                projects_payload,
                preferences_payload,
            ),
            schema=MatchSuggestions,
            tool_name=match_requirements.TOOL_NAME,
            tool_description=match_requirements.TOOL_DESCRIPTION,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Matching failed: {exc}") from exc

    suggestion_by_text = {s.requirement_text: s for s in suggestions.matches}

    with Session(engine) as session:
        # Re-matching starts fresh -- drop any previous match rows for this job.
        old_matches = session.exec(
            select(RequirementMatch).where(RequirementMatch.job_application_id == job_id)
        ).all()
        for m in old_matches:
            session.delete(m)
        session.commit()

        rows: list[RequirementMatch] = []
        for req in requirements:
            req_text = req["text"]
            suggestion = suggestion_by_text.get(req_text)
            pref = preferences_by_key.get(normalize_key(req_text))

            # Deterministic safety net: a confirmed/declined fact always wins over
            # whatever the LLM suggested, so "never ask twice" never depends on
            # the model reliably reading the preference-memory context correctly.
            if pref and pref.status == "confirmed":
                match_status, matched_skill_name, clarifying_question = "matched", pref.fact_text, None
            elif pref and pref.status == "declined":
                match_status, matched_skill_name, clarifying_question = "declined", None, None
            elif suggestion and suggestion.status == "matched":
                match_status, matched_skill_name, clarifying_question = (
                    "matched",
                    suggestion.matched_profile_item,
                    None,
                )
            elif suggestion and suggestion.status == "needs_clarification":
                match_status, matched_skill_name, clarifying_question = (
                    "needs_clarification",
                    None,
                    suggestion.suggested_question or f"Have you worked with {req_text}?",
                )
            else:
                match_status, matched_skill_name, clarifying_question = "unmatched", None, None

            row = RequirementMatch(
                job_application_id=job_id,
                requirement_text=req_text,
                requirement_category=req.get("category", "skill"),
                years_required=req.get("years_required"),
                priority=req.get("priority", "nice_to_have"),
                match_status=match_status,
                matched_skill_name=matched_skill_name,
                clarifying_question=clarifying_question,
            )
            session.add(row)
            rows.append(row)
        session.commit()
        for row in rows:
            session.refresh(row)

        match_percentage = _compute_match_percentage(rows)
        job = session.get(JobApplication, job_id)
        job.match_percentage = match_percentage
        job.status = (
            "questions_pending" if any(r.match_status == "needs_clarification" for r in rows) else "matched"
        )
        session.add(job)
        session.commit()

        return MatchSummaryResponse(
            match_percentage=match_percentage, matches=[_match_to_response(r) for r in rows]
        )


@router.get("/{job_id}/matches", response_model=MatchSummaryResponse)
def get_matches(job_id: int, user: User = Depends(get_current_user)) -> MatchSummaryResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        matches = session.exec(
            select(RequirementMatch).where(RequirementMatch.job_application_id == job_id)
        ).all()
        return MatchSummaryResponse(
            match_percentage=job.match_percentage or 0.0,
            matches=[_match_to_response(m) for m in matches],
        )


@router.patch("/{job_id}/matches/{match_id}", response_model=RequirementMatchResponse)
def answer_match_question(
    job_id: int,
    match_id: int,
    payload: AnswerQuestionRequest,
    user: User = Depends(get_current_user),
) -> RequirementMatchResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        match = session.get(RequirementMatch, match_id)
        if not match or match.job_application_id != job.id:
            raise HTTPException(status_code=404, detail="Question not found")

        match.user_answer = "yes" if payload.confirmed else "no"
        match.match_status = "matched" if payload.confirmed else "declined"
        match.resolved_at = datetime.now(timezone.utc)
        if payload.confirmed:
            match.matched_skill_name = match.requirement_text
        session.add(match)

        key = normalize_key(match.requirement_text)
        pref = session.exec(
            select(PreferenceMemory).where(
                PreferenceMemory.user_id == user.id, PreferenceMemory.normalized_key == key
            )
        ).first()
        pref_status = "confirmed" if payload.confirmed else "declined"
        question_text = match.clarifying_question or f"Have you worked with {match.requirement_text}?"
        if pref:
            pref.status = pref_status
            pref.answer_text = match.user_answer
            pref.updated_at = datetime.now(timezone.utc)
            session.add(pref)
        else:
            session.add(
                PreferenceMemory(
                    user_id=user.id,
                    normalized_key=key,
                    fact_text=match.requirement_text,
                    status=pref_status,
                    question_text=question_text,
                    answer_text=match.user_answer,
                )
            )
        session.commit()
        session.refresh(match)

        all_matches = session.exec(
            select(RequirementMatch).where(RequirementMatch.job_application_id == job_id)
        ).all()
        job.match_percentage = _compute_match_percentage(all_matches)
        if not any(m.match_status == "needs_clarification" for m in all_matches):
            job.status = "matched"
        session.add(job)
        session.commit()

        return _match_to_response(match)


@router.post("/{job_id}/generate", response_model=GenerateResumeResponse)
async def generate_job_resume(job_id: int, user: User = Depends(get_current_user)) -> GenerateResumeResponse:
    with Session(engine) as session:
        job = _get_owned_job_or_404(session, job_id, user.id)
        matches = session.exec(
            select(RequirementMatch).where(RequirementMatch.job_application_id == job_id)
        ).all()
        if not matches:
            raise HTTPException(status_code=400, detail="Run matching for this job before generating a resume.")

        base_tex = job.tex_source
        if not base_tex.strip():
            template = session.exec(
                select(ResumeTemplate).where(ResumeTemplate.user_id == user.id)
            ).first()
            if not template:
                raise HTTPException(
                    status_code=400, detail="Upload a resume template in Onboarding before generating."
                )
            base_tex = template.raw_tex

        profile_skill_names = [
            s.name for s in session.exec(select(ProfileSkill).where(ProfileSkill.user_id == user.id)).all()
        ]

        try:
            provider = get_llm_provider(session, user.id)
        except LLMNotConfiguredError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    matched = [m for m in matches if m.match_status == "matched"]
    # Only user_answer == "yes" means this fact wasn't already on the resume --
    # it came from a clarifying question the user confirmed, so it needs to be
    # added to the content, not just highlighted where it already exists. The
    # rest need a real literal term resolved for highlighting (see docstring).
    matched_terms = [
        resolve_highlight_term(m.requirement_text, m.matched_skill_name, profile_skill_names)
        for m in matched
        if m.user_answer != "yes"
    ]
    # Only skill/tool-shaped confirmations become "Additional Skills" entries --
    # a confirmed responsibility/experience item (e.g. "on-call support for a
    # 24x7 cloud service") isn't a skill keyword and reads oddly appended as
    # one; those still count as matched for the percentage, they just don't
    # get physically inserted as a fake skill line.
    confirmed_new_skills = [
        m.requirement_text
        for m in matched
        if m.user_answer == "yes" and m.requirement_category in ("skill", "tool")
    ]
    all_matched_keywords = sorted(set(matched_terms) | set(confirmed_new_skills))

    # --- Step 1: content rewrite. Only the bullets'/summary's plain text is
    # sent to the LLM (small, cheap) and spliced back by exact character
    # offset -- the model never touches surrounding LaTeX structure, so it
    # can't corrupt it. Best-effort: any failure here just skips rewriting. ---
    summary_block = extract_summary(base_tex)
    bullet_blocks = extract_bullets(base_tex)
    rewritten_tex = base_tex
    rewritten_count = 0

    if bullet_blocks or summary_block:
        try:
            plan = await provider.extract_structured(
                system_prompt=rewrite_content.REWRITE_SYSTEM_PROMPT,
                user_prompt=rewrite_content.build_rewrite_prompt(
                    all_matched_keywords,
                    confirmed_new_skills,
                    summary_block.text if summary_block else None,
                    [b.text for b in bullet_blocks],
                ),
                schema=ContentRewritePlan,
                tool_name=rewrite_content.REWRITE_TOOL_NAME,
                tool_description=rewrite_content.REWRITE_TOOL_DESCRIPTION,
                max_tokens=2048,
            )
            all_blocks = ([summary_block] if summary_block else []) + bullet_blocks
            offset = 1 if summary_block else 0
            rewrites: dict[int, str] = {}
            for r in plan.rewrites:
                if r.index == -1 and summary_block:
                    rewrites[0] = r.rewritten_text
                elif r.index >= 0 and r.index + offset < len(all_blocks):
                    rewrites[r.index + offset] = r.rewritten_text
            if rewrites:
                rewritten_tex = apply_text_rewrites(base_tex, rewrites, all_blocks)
                rewritten_count = len(rewrites)
        except Exception:
            rewritten_tex = base_tex

    # --- Step 2: deterministic highlight + append confirmed-new skills. ---
    generated, highlighted, added = generate_tailored_resume(rewritten_tex, matched_terms, confirmed_new_skills)

    # --- Step 3: compile. If the rewrite produced LaTeX that doesn't compile,
    # fall back to the highlight-only version (no rewrite) rather than saving
    # something broken or giving up entirely. ---
    compile_result = await compile_tex(generated, job_id=f"gen-{job_id}")
    if compile_result.status != "success" or not compile_result.pdf_bytes:
        fallback_generated, fallback_highlighted, fallback_added = generate_tailored_resume(
            base_tex, matched_terms, confirmed_new_skills
        )
        fallback_result = await compile_tex(fallback_generated, job_id=f"gen-{job_id}-fallback")
        if fallback_result.status != "success" or not fallback_result.pdf_bytes:
            raise HTTPException(
                status_code=502, detail=f"Resume failed to compile: {fallback_result.message or fallback_result.log}"
            )
        generated, highlighted, added = fallback_generated, fallback_highlighted, fallback_added
        compile_result = fallback_result
        rewritten_count = 0
        warning: str | None = (
            "Content rewriting produced LaTeX that didn't compile, so this used highlighting only "
            "(no bullet rewrites)."
        )
    else:
        warning = None

    # --- Step 4: iterative compile-and-trim loop to fit one page. ---
    trimmed_count = 0
    try:
        final_page_count: int | None = count_pdf_pages(compile_result.pdf_bytes)
    except Exception:
        final_page_count = None

    trim_error: str | None = None
    if final_page_count and final_page_count > 1:
        current_tex = generated
        for _ in range(MAX_TRIM_ITERATIONS):
            current_bullets = extract_bullets(current_tex)
            if not current_bullets:
                break

            trim_plan = None
            for retry in range(2):
                try:
                    trim_plan = await provider.extract_structured(
                        system_prompt=rewrite_content.TRIM_SYSTEM_PROMPT,
                        user_prompt=rewrite_content.build_trim_prompt(
                            all_matched_keywords,
                            [b.text for b in current_bullets],
                            how_many_to_remove=max(2, len(current_bullets) // 3),
                        ),
                        schema=TrimPlan,
                        tool_name=rewrite_content.TRIM_TOOL_NAME,
                        tool_description=rewrite_content.TRIM_TOOL_DESCRIPTION,
                        max_tokens=512,
                    )
                    break
                except Exception as exc:
                    trim_error = str(exc)
                    # Both rate limits and "model did not call a tool" have
                    # been observed to be transient/probabilistic on smaller
                    # free-tier models -- the exact same call has succeeded
                    # moments later under identical conditions in testing.
                    # Worth one delayed retry rather than giving up immediately.
                    if retry == 0:
                        wait = 15 if "rate_limit" in trim_error.lower() else 3
                        await asyncio.sleep(wait)
                        continue
                    break
            if trim_plan is None:
                break

            valid_indices = filter_safe_trim_indices(current_tex, current_bullets, trim_plan.indices_to_remove)
            if not valid_indices:
                break

            trimmed_tex = remove_bullets(current_tex, current_bullets, valid_indices)
            trim_result = await compile_tex(trimmed_tex, job_id=f"gen-{job_id}-trim")
            if trim_result.status != "success" or not trim_result.pdf_bytes:
                break

            trimmed_count += len(valid_indices)
            current_tex = trimmed_tex
            compile_result = trim_result
            final_page_count = count_pdf_pages(trim_result.pdf_bytes)
            trim_error = None
            if final_page_count <= 1:
                break

        generated = current_tex
        if final_page_count and final_page_count > 1:
            warning = (
                f"Could not automatically trim to one page (currently {final_page_count} pages) -- "
                "edit manually in the editor."
            )
            if trim_error:
                warning += f" (Trimming stopped early: {trim_error})"

    with Session(engine) as session:
        job = session.get(JobApplication, job_id)
        job.tex_source = generated
        job.status = "generated"
        session.add(job)
        session.commit()

    return GenerateResumeResponse(
        tex_source=generated,
        skills_added=added,
        keywords_highlighted=highlighted,
        bullets_rewritten=rewritten_count,
        bullets_trimmed=trimmed_count,
        final_page_count=final_page_count,
        warning=warning,
    )
