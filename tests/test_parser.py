"""Tests for the regex-based resume parser."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.parser import parse_resume

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data" / "resumes"


def _load_sample(name: str) -> str:
    path = SAMPLE_DIR / name
    if not path.exists():
        pytest.skip(f"Sample {name} not found")
    return path.read_text(encoding="utf-8")


class TestContactExtraction:
    """Test extraction of contact information."""

    def test_email_extraction(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert result.email == "alice.johnson@email.com"

    def test_phone_extraction(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert result.phone is not None
        assert "555" in result.phone

    def test_linkedin_extraction(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert result.linkedin is not None
        assert "linkedin.com" in result.linkedin

    def test_github_extraction(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert result.github is not None
        assert "github.com" in result.github


class TestNameExtraction:
    """Test name extraction heuristic."""

    def test_name_from_first_line(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert result.name == "Alice Johnson"

    def test_bob_name(self):
        text = _load_sample("bob_kumar_devops.txt")
        result = parse_resume(text)
        assert result.name == "Bob Kumar"

    def test_name_not_education_heading(self):
        """Regression: PDF extraction can put 'Education' before the name."""
        text = "Education\nBachelor of Science\nMIT\n\nTridib Banik\ntridib@email.com"
        result = parse_resume(text)
        assert result.name != "Education"
        assert result.name == "Tridib Banik"

    def test_name_not_skills_heading(self):
        """Section heading 'Skills' should not be returned as a name."""
        text = "Skills\nPython, Java, Docker\n\nJohn Doe\njohn@email.com"
        result = parse_resume(text)
        assert result.name != "Skills"
        assert result.name == "John Doe"

    def test_name_not_summary_heading(self):
        """Section heading 'Summary' should not be returned as a name."""
        text = "Summary\nExperienced engineer\n\nJane Smith\njane@email.com"
        result = parse_resume(text)
        assert result.name != "Summary"
        assert result.name == "Jane Smith"

    def test_name_not_experience_heading(self):
        """Section heading 'Experience' should not be returned as a name."""
        text = "Experience\nSoftware Engineer at Acme\n\nBob Lee\nbob@email.com"
        result = parse_resume(text)
        assert result.name != "Experience"

    def test_name_before_heading_still_works(self):
        """Name appearing before section headings should still be extracted."""
        text = "Alice Johnson\nalice@email.com\n\nEducation\nBachelor of Science"
        result = parse_resume(text)
        assert result.name == "Alice Johnson"


class TestSkillExtraction:
    """Test skill extraction from taxonomy and skills section."""

    def test_extracts_known_skills(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        skills_lower = [s.lower() for s in result.skills]

        assert "python" in skills_lower
        assert "react" in skills_lower or "react.js" in skills_lower
        assert "docker" in skills_lower
        assert "aws" in skills_lower

    def test_no_skills_for_irrelevant(self):
        """Marketing resume should not have many tech skills."""
        text = _load_sample("dave_wilson_marketing.txt")
        result = parse_resume(text)
        skills_lower = [s.lower() for s in result.skills]

        assert "react" not in skills_lower
        assert "python" not in skills_lower
        assert "kubernetes" not in skills_lower

    def test_devops_skills(self):
        text = _load_sample("bob_kumar_devops.txt")
        result = parse_resume(text)
        skills_lower = [s.lower() for s in result.skills]

        assert "docker" in skills_lower
        assert "kubernetes" in skills_lower or "k8s" in skills_lower
        assert "terraform" in skills_lower


class TestSectionDetection:
    """Test that sections are properly detected and split."""

    def test_experience_section_found(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert len(result.experience) > 0

    def test_education_section_found(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert len(result.education) > 0

    def test_projects_section_found(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert len(result.projects) > 0

    def test_certifications_found(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert len(result.certifications) > 0


class TestExperienceExtraction:
    """Test work experience parsing."""

    def test_multiple_experience_entries(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        assert len(result.experience) >= 2

    def test_experience_has_dates(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        has_dates = any(e.start_date for e in result.experience)
        assert has_dates, "At least one experience should have a start date"


class TestTotalYears:
    """Test total years of experience estimation."""

    def test_alice_has_significant_experience(self):
        text = _load_sample("alice_johnson_senior_dev.txt")
        result = parse_resume(text)
        if result.total_years_experience:
            assert result.total_years_experience >= 4.0

    def test_carol_has_less_experience(self):
        text = _load_sample("carol_chen_junior_analyst.txt")
        result = parse_resume(text)
        if result.total_years_experience:
            assert result.total_years_experience <= 5.0


class TestFullParse:
    """Integration tests: parse all sample resumes end-to-end."""

    def test_all_samples_parse_without_error(self):
        if not SAMPLE_DIR.exists():
            pytest.skip("Sample data not found")

        for txt_file in SAMPLE_DIR.glob("*.txt"):
            text = txt_file.read_text(encoding="utf-8")
            result = parse_resume(text)
            assert result.name is not None or len(result.skills) > 0, \
                f"Failed to extract anything from {txt_file.name}"
