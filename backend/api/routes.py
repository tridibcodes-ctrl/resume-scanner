"""API route definitions for the Resume Screener."""

import json
import logging
import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

from config import settings
from models import database as db
from models.schemas import (
    SessionCreateResponse,
    ResumeUploadResponse,
    JobDescriptionRequest,
    JobDescriptionResponse,
    AnalyzeRequest,
    SessionResultsResponse,
    CandidateResult,
    HealthResponse,
    ErrorResponse,
    ParsedResume,
    JobRequirements,
    MatchAnalysis,
)
from services.extractor import extract_text_from_bytes
from services.parser import parse_resume, parse_job_description
from services.scorer import (
    extract_resume_with_llm,
    extract_jd_with_llm,
    analyze_match_with_llm,
    merge_parsed_resume,
    convert_jd_extraction,
    rank_candidates,
)
from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ─── Health Check ────────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check application health and LLM provider availability."""
    client = get_llm_client()
    return HealthResponse(
        status="ok",
        llm_providers=client.get_provider_status(),
        database="connected",
    )


# ─── Session Management ─────────────────────────────────────────────────────


@router.post("/session", response_model=SessionCreateResponse)
async def create_session():
    """Create a new analysis session."""
    session_id = await db.create_session()
    return SessionCreateResponse(session_id=session_id)


# ─── Resume Upload ───────────────────────────────────────────────────────────


@router.post("/session/{session_id}/resumes", response_model=list[ResumeUploadResponse])
async def upload_resumes(
    session_id: str,
    files: list[UploadFile] = File(...),
):
    """Upload one or more resume files (PDF or TXT)."""
    # Validate session exists
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check candidate count limit
    current_count = await db.get_session_candidate_count(session_id)
    if current_count + len(files) > settings.max_resumes_per_session:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_resumes_per_session} resumes per session",
        )

    results = []
    for file in files:
        # Validate file type
        ext = Path(file.filename or "unknown").suffix.lower()
        if ext not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: {settings.allowed_extensions}",
            )

        # Read file bytes
        file_bytes = await file.read()

        # Validate file size
        if len(file_bytes) > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds {settings.max_file_size_mb}MB limit",
            )

        # Extract text
        try:
            raw_text = extract_text_from_bytes(file_bytes, file.filename or "upload.pdf")
        except Exception as e:
            logger.error(f"Text extraction failed for {file.filename}: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract text from {file.filename}: {str(e)}",
            )

        if not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail=f"No text content found in {file.filename}. Is it a scanned/image PDF?",
            )

        # Store in database
        candidate_id = await db.create_candidate(
            session_id=session_id,
            filename=file.filename or "unknown",
            raw_text=raw_text,
        )

        # Run regex parser immediately and store
        parsed = parse_resume(raw_text)
        await db.update_candidate_parsed(
            candidate_id=candidate_id,
            parsed_resume_json=parsed.model_dump_json(),
        )

        results.append(ResumeUploadResponse(
            session_id=session_id,
            candidate_id=candidate_id,
            filename=file.filename or "unknown",
        ))

    return results


# ─── Job Description ─────────────────────────────────────────────────────────


@router.post("/session/{session_id}/job-description", response_model=JobDescriptionResponse)
async def submit_job_description(
    session_id: str,
    body: JobDescriptionRequest,
):
    """Submit a job description for the session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.update_session_jd(session_id, body.text)
    return JobDescriptionResponse(session_id=session_id)


# ─── Analysis Pipeline ──────────────────────────────────────────────────────


@router.post("/session/{session_id}/analyze", response_model=SessionResultsResponse)
async def analyze_session(
    session_id: str,
    body: AnalyzeRequest | None = None,
):
    """
    Run the full analysis pipeline for a session.
    
    1. LLM-extract structured data from each resume
    2. LLM-extract structured requirements from the JD
    3. LLM-analyze match for each candidate
    4. Rank candidates by score
    """
    # Validate session
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session["job_description_text"]:
        raise HTTPException(status_code=400, detail="No job description submitted")

    candidates = await db.get_candidates_by_session(session_id)
    if not candidates:
        raise HTTPException(status_code=400, detail="No resumes uploaded")

    await db.update_session_status(session_id, "analyzing")

    # Step 1: Extract JD requirements via LLM
    jd_text = session["job_description_text"]
    jd_requirements = None

    if session.get("job_requirements_json"):
        # Reuse cached JD parse
        jd_requirements = JobRequirements.model_validate_json(session["job_requirements_json"])
    else:
        llm_jd = await extract_jd_with_llm(jd_text)
        if llm_jd:
            jd_requirements = convert_jd_extraction(llm_jd)
            await db.update_session_jd(
                session_id, jd_text, jd_requirements.model_dump_json()
            )

    if not jd_requirements:
        # Fallback: use deterministic JD parser
        logger.info("Using deterministic JD parser (no LLM available)")
        jd_requirements = parse_job_description(jd_text)
        await db.update_session_jd(
            session_id, jd_text, jd_requirements.model_dump_json()
        )

    # Step 2: Process candidates concurrently
    similarity_scores = body.similarity_scores if body else None
    sem = asyncio.Semaphore(2)

    async def _process_candidate(candidate: dict) -> CandidateResult | None:
        async with sem:
            candidate_id = candidate["id"]
            raw_text = candidate["raw_text"]
            filename = candidate["filename"]

            # Get regex-parsed resume
            regex_parsed = ParsedResume.model_validate_json(candidate["parsed_resume_json"])

            # LLM-enhanced extraction
            llm_parsed = await extract_resume_with_llm(raw_text)
            merged_resume = merge_parsed_resume(regex_parsed, llm_parsed)

            # Update stored parsed data with merged version
            await db.update_candidate_parsed(
                candidate_id, merged_resume.model_dump_json()
            )

            # Get candidate-specific similarity scores
            cand_similarities = (
                similarity_scores.get(candidate_id) if similarity_scores else None
            )

            # Match analysis
            match_analysis = await analyze_match_with_llm(
                merged_resume, jd_requirements, cand_similarities
            )

            if match_analysis is None:
                return None

            # Store analysis
            await db.update_candidate_analysis(
                candidate_id,
                match_analysis.model_dump_json(),
                match_analysis.overall_score,
            )

            return CandidateResult(
                candidate_id=candidate_id,
                filename=filename,
                name=merged_resume.name,
                parsed_resume=merged_resume,
                match_analysis=match_analysis,
            )

    results = await asyncio.gather(*[_process_candidate(c) for c in candidates])
    candidate_results = [r for r in results if r is not None]

    # Step 3: Rank candidates
    ranked = rank_candidates(candidate_results)

    await db.update_session_status(session_id, "completed")

    return SessionResultsResponse(
        session_id=session_id,
        job_title=jd_requirements.title,
        candidates=ranked,
        total_candidates=len(ranked),
    )


# ─── Get Results ─────────────────────────────────────────────────────────────


@router.get("/session/{session_id}/results", response_model=SessionResultsResponse)
async def get_results(session_id: str):
    """Get ranked results for a completed session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    candidates = await db.get_candidates_by_session(session_id)

    jd_title = None
    if session.get("job_requirements_json"):
        jd_req = JobRequirements.model_validate_json(session["job_requirements_json"])
        jd_title = jd_req.title

    candidate_results = []
    for c in candidates:
        if not c.get("match_analysis_json"):
            continue
        candidate_results.append(CandidateResult(
            candidate_id=c["id"],
            filename=c["filename"],
            name=ParsedResume.model_validate_json(c["parsed_resume_json"]).name if c.get("parsed_resume_json") else None,
            parsed_resume=ParsedResume.model_validate_json(c["parsed_resume_json"]) if c.get("parsed_resume_json") else ParsedResume(),
            match_analysis=MatchAnalysis.model_validate_json(c["match_analysis_json"]),
        ))

    ranked = rank_candidates(candidate_results)

    return SessionResultsResponse(
        session_id=session_id,
        job_title=jd_title,
        candidates=ranked,
        total_candidates=len(ranked),
    )


# ─── Delete Session ──────────────────────────────────────────────────────────


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all associated data."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete_session(session_id)
    return {"message": "Session deleted"}
