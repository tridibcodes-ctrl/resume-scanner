"""Scoring engine — aggregates deterministic, semantic, and LLM analysis."""

import json
import logging
from models.schemas import (
    ParsedResume,
    JobRequirements,
    MatchAnalysis,
    MatchClassification,
    LLMMatchAnalysis,
    LLMResumeExtraction,
    LLMJobExtraction,
    SkillMatch,
    CandidateResult,
)
from services.llm_client import get_llm_client, LLMError
from prompts.resume_extract import build_resume_extract_messages
from prompts.jd_extract import build_jd_extract_messages
from prompts.match_analysis import build_match_analysis_messages

logger = logging.getLogger(__name__)


# ─── LLM-Powered Extraction ─────────────────────────────────────────────────


async def extract_resume_with_llm(resume_text: str) -> LLMResumeExtraction | None:
    """Use the LLM to do deep structured extraction from resume text."""
    client = get_llm_client()
    if not client.is_available:
        logger.warning("No LLM available — skipping LLM resume extraction")
        return None

    try:
        messages = build_resume_extract_messages(resume_text)
        result = await client.structured_completion(
            messages=messages,
            response_schema=LLMResumeExtraction,
        )
        return result
    except LLMError as e:
        logger.error(f"LLM resume extraction failed: {e}")
        return None


async def extract_jd_with_llm(jd_text: str) -> LLMJobExtraction | None:
    """Use the LLM to parse job description into structured requirements."""
    client = get_llm_client()
    if not client.is_available:
        logger.warning("No LLM available — skipping LLM JD extraction")
        return None

    try:
        messages = build_jd_extract_messages(jd_text)
        result = await client.structured_completion(
            messages=messages,
            response_schema=LLMJobExtraction,
        )
        return result
    except LLMError as e:
        logger.error(f"LLM JD extraction failed: {e}")
        return None


async def analyze_match_with_llm(
    parsed_resume: ParsedResume,
    job_requirements: JobRequirements,
    similarity_scores: dict | None = None,
) -> MatchAnalysis | None:
    """Use the LLM to produce a detailed match analysis."""
    client = get_llm_client()
    if not client.is_available:
        logger.warning("No LLM available — using deterministic scoring only")
        return _deterministic_match(parsed_resume, job_requirements)

    try:
        resume_json = parsed_resume.model_dump_json(indent=2)
        jd_json = job_requirements.model_dump_json(indent=2)
        sim_json = json.dumps(similarity_scores, indent=2) if similarity_scores else None

        messages = build_match_analysis_messages(resume_json, jd_json, sim_json)
        llm_result = await client.structured_completion(
            messages=messages,
            response_schema=LLMMatchAnalysis,
        )

        # Validate and convert to MatchAnalysis
        classification = _classify_score(llm_result.overall_score)

        return MatchAnalysis(
            overall_score=llm_result.overall_score,
            classification=classification,
            skills_score=llm_result.skills_score,
            experience_score=llm_result.experience_score,
            education_score=llm_result.education_score,
            project_score=llm_result.project_score,
            matched_skills=llm_result.matched_skills,
            missing_skills=llm_result.missing_skills,
            strengths=llm_result.strengths,
            weaknesses=llm_result.weaknesses,
            justification=llm_result.justification,
        )
    except LLMError as e:
        logger.error(f"LLM match analysis failed: {e}")
        return _deterministic_match(parsed_resume, job_requirements)


# ─── Merge Parsed Data ───────────────────────────────────────────────────────


def merge_parsed_resume(
    regex_parsed: ParsedResume, llm_parsed: LLMResumeExtraction | None
) -> ParsedResume:
    """
    Merge regex-parsed data with LLM-parsed data.
    LLM data takes priority for structured fields; regex provides fallback.
    """
    if llm_parsed is None:
        return regex_parsed

    # Merge skills: union of both
    all_skills = set(s.lower() for s in regex_parsed.skills)
    merged_skills = list(regex_parsed.skills)  # Keep regex casing
    for skill in llm_parsed.skills:
        if skill.lower() not in all_skills:
            merged_skills.append(skill)
            all_skills.add(skill.lower())

    return ParsedResume(
        name=llm_parsed.name or regex_parsed.name,
        email=llm_parsed.email or regex_parsed.email,
        phone=llm_parsed.phone or regex_parsed.phone,
        linkedin=llm_parsed.linkedin or regex_parsed.linkedin,
        github=llm_parsed.github or regex_parsed.github,
        summary=llm_parsed.summary or regex_parsed.summary,
        skills=sorted(merged_skills, key=str.lower),
        experience=llm_parsed.experience if llm_parsed.experience else regex_parsed.experience,
        education=llm_parsed.education if llm_parsed.education else regex_parsed.education,
        projects=llm_parsed.projects if llm_parsed.projects else regex_parsed.projects,
        certifications=llm_parsed.certifications if llm_parsed.certifications else regex_parsed.certifications,
        total_years_experience=llm_parsed.total_years_experience or regex_parsed.total_years_experience,
    )


def convert_jd_extraction(llm_jd: LLMJobExtraction) -> JobRequirements:
    """Convert LLM JD extraction to JobRequirements model."""
    return JobRequirements(
        title=llm_jd.title,
        required_skills=llm_jd.required_skills,
        preferred_skills=llm_jd.preferred_skills,
        min_experience_years=llm_jd.min_experience_years,
        education_requirement=llm_jd.education_requirement,
        responsibilities=llm_jd.responsibilities,
    )


# ─── Deterministic Scoring (Fallback) ────────────────────────────────────────


def _deterministic_match(
    resume: ParsedResume, job: JobRequirements
) -> MatchAnalysis:
    """
    Produce a match analysis using only deterministic keyword matching.
    Used as fallback when LLM is unavailable.
    """
    resume_skills_lower = {s.lower() for s in resume.skills}
    required_lower = {s.lower() for s in job.required_skills}

    matched = []
    missing = []

    for req_skill in job.required_skills:
        req_lower = req_skill.lower()
        if req_lower in resume_skills_lower:
            matched.append(SkillMatch(
                required_skill=req_skill,
                candidate_skill=req_skill,
                evidence="Listed in skills section",
                similarity=1.0,
            ))
        else:
            # Check for partial/substring matches
            found = False
            for res_skill in resume.skills:
                if req_lower in res_skill.lower() or res_skill.lower() in req_lower:
                    matched.append(SkillMatch(
                        required_skill=req_skill,
                        candidate_skill=res_skill,
                        evidence="Partial match in skills",
                        similarity=0.75,
                    ))
                    found = True
                    break
            if not found:
                missing.append(req_skill)

    # Calculate scores
    skills_score = int((len(matched) / max(len(job.required_skills), 1)) * 100)

    # Experience: simple check on years
    exp_score = 50  # default
    if job.min_experience_years and resume.total_years_experience:
        ratio = resume.total_years_experience / job.min_experience_years
        exp_score = min(int(ratio * 100), 100)

    # Education: basic check
    edu_score = 50 if resume.education else 25

    # Projects
    project_score = min(len(resume.projects) * 25, 100) if resume.projects else 0

    # Weighted overall
    overall = int(
        skills_score * 0.35
        + exp_score * 0.35
        + edu_score * 0.15
        + project_score * 0.15
    )

    classification = _classify_score(overall)

    # Generate basic strengths/weaknesses
    strengths = []
    weaknesses = []
    if matched:
        strengths.append(f"Has {len(matched)} of {len(job.required_skills)} required skills")
    if resume.total_years_experience:
        strengths.append(f"{resume.total_years_experience} years of professional experience")
    if missing:
        weaknesses.append(f"Missing {len(missing)} required skills: {', '.join(missing[:5])}")
    if not resume.projects:
        weaknesses.append("No projects listed")

    justification = (
        f"Candidate matches {len(matched)} of {len(job.required_skills)} required skills. "
        f"{'Has ' + str(resume.total_years_experience) + ' years of experience. ' if resume.total_years_experience else ''}"
        f"{'Missing key skills: ' + ', '.join(missing[:3]) + '. ' if missing else ''}"
        f"Overall assessment: {classification.value}."
    )

    return MatchAnalysis(
        overall_score=overall,
        classification=classification,
        skills_score=skills_score,
        experience_score=exp_score,
        education_score=edu_score,
        project_score=project_score,
        matched_skills=matched,
        missing_skills=missing,
        strengths=strengths or ["Resume provided"],
        weaknesses=weaknesses or ["Limited information available"],
        justification=justification,
    )


def rank_candidates(candidates: list[CandidateResult]) -> list[CandidateResult]:
    """Sort candidates by overall score, descending."""
    return sorted(
        candidates,
        key=lambda c: c.match_analysis.overall_score,
        reverse=True,
    )


def _classify_score(score: int) -> MatchClassification:
    """Classify a score into Strong/Moderate/Weak."""
    if score >= 75:
        return MatchClassification.STRONG
    elif score >= 50:
        return MatchClassification.MODERATE
    else:
        return MatchClassification.WEAK
