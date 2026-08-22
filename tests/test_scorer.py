"""Tests for the scoring engine."""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from models.schemas import (
    ParsedResume,
    ResumeExperience,
    ResumeEducation,
    ResumeProject,
    JobRequirements,
    MatchClassification,
    CandidateResult,
)
from services.scorer import _deterministic_match, _classify_score, rank_candidates


class TestClassifyScore:
    """Test score classification boundaries."""

    def test_strong_match(self):
        assert _classify_score(75) == MatchClassification.STRONG
        assert _classify_score(100) == MatchClassification.STRONG
        assert _classify_score(80) == MatchClassification.STRONG

    def test_moderate_match(self):
        assert _classify_score(50) == MatchClassification.MODERATE
        assert _classify_score(74) == MatchClassification.MODERATE
        assert _classify_score(60) == MatchClassification.MODERATE

    def test_weak_match(self):
        assert _classify_score(49) == MatchClassification.WEAK
        assert _classify_score(0) == MatchClassification.WEAK
        assert _classify_score(25) == MatchClassification.WEAK


class TestDeterministicMatch:
    """Test the deterministic (no-LLM) matching engine."""

    def _make_job(self, required_skills, min_exp=None, edu=None):
        return JobRequirements(
            title="Test Engineer",
            required_skills=required_skills,
            preferred_skills=[],
            min_experience_years=min_exp,
            education_requirement=edu,
            responsibilities=["Build things"],
        )

    def _make_resume(self, skills, years=None, has_edu=True, projects=None):
        return ParsedResume(
            name="Test Candidate",
            email="test@test.com",
            skills=skills,
            experience=[ResumeExperience(
                company="TestCo", title="Developer",
                start_date="Jan 2020", end_date="Present",
                description="Did stuff",
            )],
            education=[ResumeEducation(
                institution="TestU", degree="B.S.",
                field="CS", year=2020,
            )] if has_edu else [],
            projects=projects or [],
            total_years_experience=years,
        )

    def test_perfect_skill_match(self):
        job = self._make_job(["Python", "React", "Docker"])
        resume = self._make_resume(["Python", "React", "Docker"])
        result = _deterministic_match(resume, job)

        assert result.skills_score == 100
        assert len(result.matched_skills) == 3
        assert len(result.missing_skills) == 0

    def test_partial_skill_match(self):
        job = self._make_job(["Python", "React", "Docker", "AWS"])
        resume = self._make_resume(["Python", "React"])
        result = _deterministic_match(resume, job)

        assert result.skills_score == 50
        assert len(result.matched_skills) == 2
        assert len(result.missing_skills) == 2

    def test_no_skill_match(self):
        job = self._make_job(["Python", "React", "Docker"])
        resume = self._make_resume(["Marketing", "Sales"])
        result = _deterministic_match(resume, job)

        assert result.skills_score == 0
        assert len(result.missing_skills) == 3

    def test_experience_years_scoring(self):
        job = self._make_job(["Python"], min_exp=5)
        resume = self._make_resume(["Python"], years=5.0)
        result = _deterministic_match(resume, job)
        assert result.experience_score == 100

    def test_insufficient_experience(self):
        job = self._make_job(["Python"], min_exp=10)
        resume = self._make_resume(["Python"], years=3.0)
        result = _deterministic_match(resume, job)
        assert result.experience_score == 30

    def test_overall_score_is_weighted(self):
        job = self._make_job(["Python", "React", "Docker", "AWS"])
        resume = self._make_resume(["Python", "React"], years=5.0)
        result = _deterministic_match(resume, job)

        # Overall should be between 0 and 100
        assert 0 <= result.overall_score <= 100

    def test_classification_matches_score(self):
        job = self._make_job(["Python"])
        resume = self._make_resume(["Python"], years=10.0)
        result = _deterministic_match(resume, job)

        if result.overall_score >= 75:
            assert result.classification == MatchClassification.STRONG
        elif result.overall_score >= 50:
            assert result.classification == MatchClassification.MODERATE

    def test_justification_not_empty(self):
        job = self._make_job(["Python"])
        resume = self._make_resume(["Python"])
        result = _deterministic_match(resume, job)
        assert len(result.justification) > 20

    def test_strengths_and_weaknesses(self):
        job = self._make_job(["Python", "React", "Docker"])
        resume = self._make_resume(["Python"])
        result = _deterministic_match(resume, job)
        assert len(result.strengths) > 0
        assert len(result.weaknesses) > 0

    def test_substring_matching(self):
        """Test that partial/substring matches work (e.g., 'React.js' matches 'React')."""
        job = self._make_job(["React"])
        resume = self._make_resume(["React.js"])
        result = _deterministic_match(resume, job)

        # Should find at least a partial match
        assert len(result.matched_skills) >= 1 or result.skills_score > 0


class TestRankCandidates:
    """Test candidate ranking."""

    def _make_candidate(self, name, score):
        analysis = _deterministic_match(
            ParsedResume(name=name, skills=["Python"]),
            JobRequirements(title="Dev", required_skills=["Python"]),
        )
        # Override score for testing
        analysis.overall_score = score
        return CandidateResult(
            candidate_id=f"id-{name}",
            filename=f"{name}.txt",
            name=name,
            parsed_resume=ParsedResume(name=name, skills=["Python"]),
            match_analysis=analysis,
        )

    def test_ranks_by_score_descending(self):
        candidates = [
            self._make_candidate("Low", 30),
            self._make_candidate("High", 90),
            self._make_candidate("Mid", 60),
        ]
        ranked = rank_candidates(candidates)

        assert ranked[0].name == "High"
        assert ranked[1].name == "Mid"
        assert ranked[2].name == "Low"

    def test_empty_list(self):
        assert rank_candidates([]) == []
