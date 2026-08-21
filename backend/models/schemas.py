"""Pydantic schemas for API requests/responses and LLM structured output."""

from __future__ import annotations
from pydantic import BaseModel, Field
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────


class MatchClassification(str, Enum):
    STRONG = "Strong Match"
    MODERATE = "Moderate Match"
    WEAK = "Weak Match"


# ─── Resume Structures ───────────────────────────────────────────────────────


class ResumeExperience(BaseModel):
    """A single work experience entry."""
    company: str = Field(description="Company or organization name")
    title: str = Field(description="Job title or role")
    start_date: str | None = Field(default=None, description="Start date (e.g. 'Jan 2020')")
    end_date: str | None = Field(default=None, description="End date or 'Present'")
    description: str = Field(default="", description="Role description and accomplishments")
    duration_months: int | None = Field(default=None, description="Estimated duration in months")


class ResumeEducation(BaseModel):
    """A single education entry."""
    institution: str = Field(description="University or institution name")
    degree: str = Field(description="Degree type (e.g. 'B.S.', 'Master of Science')")
    field: str | None = Field(default=None, description="Field of study")
    year: int | None = Field(default=None, description="Graduation year")


class ResumeProject(BaseModel):
    """A single project entry."""
    name: str = Field(description="Project name or title")
    description: str = Field(default="", description="What the project does")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")


class ParsedResume(BaseModel):
    """Fully parsed and structured resume data."""
    name: str | None = Field(default=None, description="Candidate's full name")
    email: str | None = Field(default=None, description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    linkedin: str | None = Field(default=None, description="LinkedIn profile URL")
    github: str | None = Field(default=None, description="GitHub profile URL")
    summary: str | None = Field(default=None, description="Professional summary or objective")
    skills: list[str] = Field(default_factory=list, description="List of skills and technologies")
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    total_years_experience: float | None = Field(
        default=None, description="Total years of professional experience"
    )


# ─── Job Description Structures ──────────────────────────────────────────────


class JobRequirements(BaseModel):
    """Structured job description requirements."""
    title: str = Field(description="Job title")
    required_skills: list[str] = Field(default_factory=list, description="Must-have skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    min_experience_years: float | None = Field(
        default=None, description="Minimum years of experience required"
    )
    education_requirement: str | None = Field(
        default=None, description="Required education level (e.g. 'Bachelor's in CS')"
    )
    responsibilities: list[str] = Field(
        default_factory=list, description="Key job responsibilities"
    )


# ─── Match Analysis Structures ───────────────────────────────────────────────


class SkillMatch(BaseModel):
    """A single matched skill with evidence."""
    required_skill: str = Field(description="The skill from the job description")
    candidate_skill: str = Field(description="The matching skill from the resume")
    evidence: str = Field(description="Where in the resume this skill appears")
    similarity: float = Field(description="Similarity score 0.0-1.0")


class MatchAnalysis(BaseModel):
    """Complete match analysis for a candidate against a job description."""
    overall_score: int = Field(ge=0, le=100, description="Overall match score 0-100")
    classification: MatchClassification = Field(description="Match classification")
    skills_score: int = Field(ge=0, le=100, description="Skills match score 0-100")
    experience_score: int = Field(ge=0, le=100, description="Experience relevance score 0-100")
    education_score: int = Field(ge=0, le=100, description="Education alignment score 0-100")
    project_score: int = Field(ge=0, le=100, description="Project relevance score 0-100")
    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list, description="Required skills not found")
    strengths: list[str] = Field(default_factory=list, description="Candidate's key strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Candidate's gaps")
    justification: str = Field(
        description="3-5 sentence explanation of the match assessment"
    )


# ─── LLM Output Schemas ─────────────────────────────────────────────────────
# These are the schemas passed to the LLM's response_format parameter.


class LLMResumeExtraction(BaseModel):
    """Schema for LLM-based resume extraction."""
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    projects: list[ResumeProject] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    total_years_experience: float | None = None


class LLMJobExtraction(BaseModel):
    """Schema for LLM-based job description extraction."""
    title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    education_requirement: str | None = None
    responsibilities: list[str] = Field(default_factory=list)


class LLMMatchAnalysis(BaseModel):
    """Schema for LLM-based match analysis output."""
    overall_score: int = Field(ge=0, le=100)
    skills_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    education_score: int = Field(ge=0, le=100)
    project_score: int = Field(ge=0, le=100)
    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    justification: str = ""


# ─── API Request / Response Models ───────────────────────────────────────────


class SessionCreateResponse(BaseModel):
    session_id: str
    message: str = "Session created"


class ResumeUploadResponse(BaseModel):
    session_id: str
    candidate_id: str
    filename: str
    message: str = "Resume uploaded and text extracted"


class JobDescriptionRequest(BaseModel):
    text: str = Field(min_length=10, description="Job description text")


class JobDescriptionResponse(BaseModel):
    session_id: str
    message: str = "Job description saved"


class AnalyzeRequest(BaseModel):
    """Optional: client-computed similarity scores from Transformers.js."""
    similarity_scores: dict[str, dict[str, float]] | None = Field(
        default=None,
        description="Map of candidate_id -> {skill: similarity_score}",
    )


class CandidateResult(BaseModel):
    """Full result for a single candidate."""
    candidate_id: str
    filename: str
    name: str | None
    parsed_resume: ParsedResume
    match_analysis: MatchAnalysis


class SessionResultsResponse(BaseModel):
    """Ranked list of candidates for a session."""
    session_id: str
    job_title: str | None = None
    candidates: list[CandidateResult] = Field(default_factory=list)
    total_candidates: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    llm_providers: dict[str, bool] = Field(default_factory=dict)
    database: str = "connected"


class ErrorResponse(BaseModel):
    detail: str
