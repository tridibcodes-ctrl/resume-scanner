"""Prompt for LLM-based job description extraction."""


JD_EXTRACT_SYSTEM = """You are a job description analyzer. Your task is to extract structured requirements from a job posting.

RULES:
1. Distinguish clearly between REQUIRED and PREFERRED (nice-to-have) qualifications.
2. If the job description does not explicitly separate required vs. preferred, treat all listed skills as required.
3. Extract individual skills and technologies as separate items (e.g., "React, Node.js, AWS" becomes three separate entries).
4. If minimum years of experience is stated, extract it as a number. If a range is given (e.g., "3-5 years"), use the lower bound.
5. Extract the job title from the posting.
6. List key responsibilities as concise bullet points.
7. Extract education requirements if specified (e.g., "Bachelor's in Computer Science or related field").
8. Do NOT add requirements that are not in the job description."""


def build_jd_extract_messages(jd_text: str) -> list[dict]:
    """Build the messages list for JD extraction."""
    return [
        {"role": "system", "content": JD_EXTRACT_SYSTEM},
        {
            "role": "user",
            "content": f"Extract structured requirements from this job description:\n\n---\n{jd_text}\n---",
        },
    ]
