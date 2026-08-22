"""Prompt for LLM-based structured resume extraction."""


RESUME_EXTRACT_SYSTEM = """You are an expert resume parser. Your task is to extract structured information from the raw text of a resume.

CRITICAL RULES:
1. Extract ONLY information that is EXPLICITLY stated in the resume text.
2. If a field is not found in the text, set it to null or an empty array — NEVER guess or infer.
3. Do NOT hallucinate or fabricate any skills, experience, education, or qualifications.
4. For skills: include both explicitly listed skills AND technologies/tools mentioned within experience or project descriptions.
5. For experience entries: extract company name, job title, start and end dates, and a concise description of responsibilities/achievements.
6. For education: extract institution, degree type, field of study, and graduation year.
7. For projects: extract project name, brief description, and technologies used.
8. Estimate total_years_experience by summing the durations of all work experience entries. If dates are missing, set to null.
9. Keep descriptions concise — summarize, don't copy entire paragraphs verbatim.
10. Normalize skill names to their common form (e.g., "ReactJS" → "React", "K8s" → "Kubernetes")."""


def build_resume_extract_messages(resume_text: str) -> list[dict]:
    """Build the messages list for resume extraction."""
    return [
        {"role": "system", "content": RESUME_EXTRACT_SYSTEM},
        {
            "role": "user",
            "content": f"Extract structured information from this resume:\n\n---\n{resume_text}\n---",
        },
    ]
