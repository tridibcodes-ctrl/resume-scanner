"""Resume parser using regex and heuristics — zero ML dependencies."""

import re
from models.schemas import ParsedResume, ResumeExperience, ResumeEducation, ResumeProject


# ─── Skill Taxonomy ──────────────────────────────────────────────────────────
# Curated list of common tech and business skills for matching.

SKILL_TAXONOMY = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "objective-c", "dart", "lua", "haskell", "elixir", "clojure", "groovy",
    # Web Frontend
    "html", "css", "react", "react.js", "reactjs", "angular", "angularjs", "vue",
    "vue.js", "vuejs", "next.js", "nextjs", "nuxt.js", "svelte", "jquery",
    "tailwind", "tailwindcss", "bootstrap", "sass", "scss", "less", "webpack",
    "vite", "redux", "mobx", "graphql", "rest", "restful",
    # Web Backend
    "node.js", "nodejs", "express", "express.js", "django", "flask", "fastapi",
    "spring", "spring boot", "rails", "ruby on rails", "asp.net", ".net",
    "laravel", "gin", "fiber", "nestjs", "nest.js",
    # Databases
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite",
    "oracle", "cassandra", "dynamodb", "elasticsearch", "neo4j", "firebase",
    "supabase", "couchdb", "mariadb", "mssql", "sql server",
    # Cloud & DevOps
    "aws", "amazon web services", "azure", "gcp", "google cloud", "docker",
    "kubernetes", "k8s", "terraform", "ansible", "jenkins", "ci/cd", "ci cd",
    "continuous integration", "continuous deployment", "github actions",
    "gitlab ci", "circleci", "travis ci", "nginx", "apache", "linux",
    "bash", "shell scripting", "powershell",
    # Data & ML
    "machine learning", "deep learning", "artificial intelligence", "ai", "ml",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas",
    "numpy", "scipy", "matplotlib", "seaborn", "jupyter", "nlp",
    "natural language processing", "computer vision", "opencv",
    "data science", "data analysis", "data engineering", "etl",
    "spark", "hadoop", "airflow", "kafka", "tableau", "power bi",
    "statistics", "statistical analysis", "data visualization",
    # Mobile
    "android", "ios", "react native", "flutter", "xamarin", "swiftui",
    "jetpack compose", "mobile development",
    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban", "tdd", "test-driven development",
    "unit testing", "integration testing", "selenium", "cypress",
    "jest", "pytest", "mocha", "postman", "swagger", "openapi",
    # Architecture
    "microservices", "monolith", "serverless", "event-driven",
    "message queue", "rabbitmq", "api design", "system design",
    "design patterns", "solid", "oop", "functional programming",
    # Security
    "cybersecurity", "security", "oauth", "jwt", "encryption",
    "penetration testing", "soc", "siem",
    # Business / Soft Skills
    "project management", "leadership", "communication",
    "problem solving", "team management", "stakeholder management",
    "product management", "business analysis", "requirements gathering",
    "technical writing", "documentation", "mentoring",
}

# Compile a pattern for efficient matching
_SKILL_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in sorted(SKILL_TAXONOMY, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# ─── Section Detection ───────────────────────────────────────────────────────

_SECTION_PATTERNS = {
    "summary": re.compile(
        r"^(?:summary|professional\s+summary|profile|objective|about\s+me|overview)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "experience": re.compile(
        r"^(?:experience|work\s+experience|professional\s+experience|employment|work\s+history|career)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "education": re.compile(
        r"^(?:education|academic|academics|qualifications|educational\s+background)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "skills": re.compile(
        r"^(?:skills|technical\s+skills|core\s+skills|technologies|tech\s+stack|competencies|proficiencies)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "projects": re.compile(
        r"^(?:projects|personal\s+projects|key\s+projects|notable\s+projects|side\s+projects)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "certifications": re.compile(
        r"^(?:certifications?|certificates?|licenses?|credentials)\s*[:\-]?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# ─── Entity Extraction Patterns ──────────────────────────────────────────────

_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)
_LINKEDIN_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?", re.IGNORECASE)
_GITHUB_PATTERN = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?", re.IGNORECASE)

_DATE_RANGE_PATTERN = re.compile(
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*\.?\s*\d{4}|(?:\d{1,2}/\d{4}))"
    r"\s*[-–—to]+\s*"
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s*\.?\s*\d{4}|Present|Current|Now|(?:\d{1,2}/\d{4}))",
    re.IGNORECASE,
)

_DEGREE_PATTERN = re.compile(
    r"\b(?:Ph\.?D\.?|Doctor(?:ate)?|M\.?S\.?|M\.?A\.?|M\.?B\.?A\.?|M\.?Tech\.?|"
    r"Master(?:'?s)?|B\.?S\.?|B\.?A\.?|B\.?E\.?|B\.?Tech\.?|Bachelor(?:'?s)?|"
    r"Associate(?:'?s)?|Diploma)\b",
    re.IGNORECASE,
)


# ─── Main Parser ─────────────────────────────────────────────────────────────


def parse_resume(text: str) -> ParsedResume:
    """
    Parse resume text using regex and heuristics.
    
    This produces a rough structured extraction. The LLM refines it later.
    Returns a ParsedResume with best-effort populated fields.
    """
    # Extract contact info
    email = _extract_first(_EMAIL_PATTERN, text)
    phone = _extract_first(_PHONE_PATTERN, text)
    linkedin = _extract_first(_LINKEDIN_PATTERN, text)
    github = _extract_first(_GITHUB_PATTERN, text)

    # Extract name (heuristic: first non-empty line that looks like a name)
    name = _extract_name(text)

    # Split into sections
    sections = _split_sections(text)

    # Extract skills from the skills section + full-text taxonomy scan
    skills = _extract_skills(text, sections.get("skills", ""))

    # Extract experience entries
    experience = _extract_experience(sections.get("experience", ""))

    # Extract education entries
    education = _extract_education(sections.get("education", ""))

    # Extract projects
    projects = _extract_projects(sections.get("projects", ""))

    # Extract certifications
    certifications = _extract_certifications(sections.get("certifications", ""))

    # Summary
    summary = sections.get("summary", "").strip() or None

    # Estimate total years
    total_years = _estimate_total_years(experience)

    return ParsedResume(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        summary=summary,
        skills=skills,
        experience=experience,
        education=education,
        projects=projects,
        certifications=certifications,
        total_years_experience=total_years,
    )


# ─── Helper Functions ────────────────────────────────────────────────────────


def _extract_first(pattern: re.Pattern, text: str) -> str | None:
    """Extract the first match of a pattern, or None."""
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def _extract_name(text: str) -> str | None:
    """
    Heuristic name extraction:
    - Take first few non-empty lines
    - Pick the one that looks most like a name (2-4 title-case words, no special chars)
    - Filters out common resume section headings that can appear early in
      PDF-extracted text due to column layouts or extraction order issues.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()][:5]
    # Require at least 2 title-case words (first + last name)
    name_pattern = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$")

    for line in lines:
        # Skip lines that are clearly emails, phones, or URLs
        if "@" in line or "http" in line or re.search(r"\d{3,}", line):
            continue
        # Skip very long lines (likely a summary)
        if len(line) > 50:
            continue
        # Skip common section headings (case-insensitive)
        if _is_section_heading(line):
            continue
        if name_pattern.match(line):
            return line

    # Fallback: just return the first short line that isn't a heading
    for line in lines:
        if (len(line) < 40
                and "@" not in line
                and "http" not in line
                and not _is_section_heading(line)):
            return line
    return None


# Words that are common resume section headings and should never be treated
# as a candidate name.  Checked case-insensitively.
_SECTION_HEADING_WORDS = {
    "summary", "professional summary", "profile", "objective", "about me",
    "overview", "experience", "work experience", "professional experience",
    "employment", "work history", "career", "education", "academic",
    "academics", "qualifications", "educational background", "skills",
    "technical skills", "core skills", "technologies", "tech stack",
    "competencies", "proficiencies", "projects", "personal projects",
    "key projects", "notable projects", "side projects", "certifications",
    "certification", "certificates", "certificate", "licenses", "license",
    "credentials", "references", "interests", "hobbies", "awards",
    "honors", "publications", "achievements", "activities",
    "volunteer", "volunteering", "languages",
}


def _is_section_heading(line: str) -> bool:
    """Return True if the line is a common resume section heading."""
    return line.strip().lower().rstrip(":-") in _SECTION_HEADING_WORDS


def _split_sections(text: str) -> dict[str, str]:
    """
    Split resume text into named sections using heading detection.
    Returns a dict mapping section name to its text content.
    """
    # Find all section heading positions
    found_sections: list[tuple[str, int, int]] = []

    for section_name, pattern in _SECTION_PATTERNS.items():
        for match in pattern.finditer(text):
            found_sections.append((section_name, match.start(), match.end()))

    if not found_sections:
        return {}

    # Sort by position in text
    found_sections.sort(key=lambda x: x[1])

    # Extract text between sections
    sections = {}
    for i, (name, start, end) in enumerate(found_sections):
        if i + 1 < len(found_sections):
            next_start = found_sections[i + 1][1]
            sections[name] = text[end:next_start].strip()
        else:
            sections[name] = text[end:].strip()

    return sections


def _extract_skills(full_text: str, skills_section: str) -> list[str]:
    """
    Extract skills from both the dedicated skills section and full text.
    Uses the curated taxonomy for matching.
    """
    found_skills = set()

    # 1. Taxonomy-based matching on full text
    for match in _SKILL_PATTERN.finditer(full_text):
        found_skills.add(match.group(0).strip())

    # 2. If there's a skills section, also grab comma/pipe/bullet separated items
    if skills_section:
        # Split by common delimiters
        items = re.split(r"[,|•·▪◦\n]", skills_section)
        for item in items:
            cleaned = item.strip().strip("-").strip("●").strip("○").strip()
            if cleaned and 2 <= len(cleaned) <= 50:
                found_skills.add(cleaned)

    # Normalize: remove duplicates case-insensitively, keep the first-seen casing
    seen_lower: dict[str, str] = {}
    for skill in found_skills:
        key = skill.lower().strip()
        if key and key not in seen_lower:
            seen_lower[key] = skill

    return sorted(seen_lower.values(), key=str.lower)


def _extract_experience(experience_text: str) -> list[ResumeExperience]:
    """
    Extract work experience entries from the experience section.
    Uses date ranges as entry delimiters.
    """
    if not experience_text:
        return []

    entries = []
    lines = experience_text.split("\n")
    current_entry: dict = {}
    current_description_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if this line contains a date range (likely a new entry)
        date_match = _DATE_RANGE_PATTERN.search(line)
        if date_match:
            # Save previous entry
            if current_entry:
                current_entry["description"] = " ".join(current_description_lines).strip()
                entries.append(current_entry)
                current_description_lines = []

            # Parse date range
            date_str = date_match.group(0)
            parts = re.split(r"\s*[-–—]\s*|\s+to\s+", date_str, maxsplit=1)
            start_date = parts[0].strip() if parts else None
            end_date = parts[1].strip() if len(parts) > 1 else None

            # The rest of the line (minus the date) might have title/company
            remaining = line[:date_match.start()].strip().rstrip("|,–-").strip()

            current_entry = {
                "start_date": start_date,
                "end_date": end_date,
                "title": remaining or "",
                "company": "",
            }
        elif current_entry and not current_entry.get("company"):
            # Second line after a date range is often the company (or vice versa)
            if not current_entry["title"]:
                current_entry["title"] = line
            else:
                current_entry["company"] = line
        else:
            current_description_lines.append(line)

    # Save last entry
    if current_entry:
        current_entry["description"] = " ".join(current_description_lines).strip()
        entries.append(current_entry)

    return [
        ResumeExperience(
            company=e.get("company", ""),
            title=e.get("title", ""),
            start_date=e.get("start_date"),
            end_date=e.get("end_date"),
            description=e.get("description", ""),
        )
        for e in entries
    ]


def _extract_education(education_text: str) -> list[ResumeEducation]:
    """Extract education entries from the education section."""
    if not education_text:
        return []

    entries = []
    lines = education_text.split("\n")
    current_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_lines:
                entry = _parse_education_block("\n".join(current_lines))
                if entry:
                    entries.append(entry)
                current_lines = []
            continue
        current_lines.append(line)

    # Last block
    if current_lines:
        entry = _parse_education_block("\n".join(current_lines))
        if entry:
            entries.append(entry)

    return entries


def _parse_education_block(block: str) -> ResumeEducation | None:
    """Parse a single education block into structured data."""
    degree_match = _DEGREE_PATTERN.search(block)
    if not degree_match:
        return None

    degree = degree_match.group(0)
    year_match = re.search(r"\b(19|20)\d{2}\b", block)
    year = int(year_match.group(0)) if year_match else None

    # Try to extract institution (usually on its own line)
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    institution = ""
    field = ""

    for line in lines:
        if degree in line:
            # Extract field from same line: "B.S. in Computer Science"
            field_match = re.search(r"(?:in|of)\s+(.+?)(?:\s*[-,]|\s*$)", line, re.IGNORECASE)
            if field_match:
                field = field_match.group(1).strip()
        elif not institution and len(line) > 3:
            institution = line

    return ResumeEducation(
        institution=institution,
        degree=degree,
        field=field or None,
        year=year,
    )


def _extract_projects(projects_text: str) -> list[ResumeProject]:
    """Extract project entries from the projects section."""
    if not projects_text:
        return []

    entries = []
    lines = projects_text.split("\n")
    current_name = ""
    current_desc_lines: list[str] = []
    current_techs: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_name:
                entries.append(ResumeProject(
                    name=current_name,
                    description=" ".join(current_desc_lines).strip(),
                    technologies=current_techs,
                ))
                current_name = ""
                current_desc_lines = []
                current_techs = []
            continue

        # Heuristic: short lines with title-case or bold markers = project name
        if (len(line) < 80 and not line.startswith(("-", "•", "●", "○", "▪"))
                and not current_name):
            current_name = line.strip(":").strip("*").strip()
        else:
            current_desc_lines.append(line)
            # Scan for tech mentions
            for match in _SKILL_PATTERN.finditer(line):
                tech = match.group(0).strip()
                if tech.lower() not in [t.lower() for t in current_techs]:
                    current_techs.append(tech)

    # Last entry
    if current_name:
        entries.append(ResumeProject(
            name=current_name,
            description=" ".join(current_desc_lines).strip(),
            technologies=current_techs,
        ))

    return entries


def _extract_certifications(certs_text: str) -> list[str]:
    """Extract certification names from the certifications section."""
    if not certs_text:
        return []

    certs = []
    for line in certs_text.split("\n"):
        line = line.strip().strip("-").strip("•").strip("●").strip()
        if line and len(line) > 3:
            certs.append(line)

    return certs


def _estimate_total_years(experience: list[ResumeExperience]) -> float | None:
    """Estimate total years of experience from date ranges."""
    if not experience:
        return None

    total_months = 0
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    for exp in experience:
        start = _parse_date(exp.start_date, month_map)
        end = _parse_date(exp.end_date, month_map)
        if start and end:
            months = (end[0] - start[0]) * 12 + (end[1] - start[1])
            if 0 < months < 360:  # Sanity check: less than 30 years
                total_months += months
                exp.duration_months = months

    return round(total_months / 12, 1) if total_months > 0 else None


def _parse_date(date_str: str | None, month_map: dict) -> tuple[int, int] | None:
    """Parse a date string into (year, month). Returns None if unparseable."""
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    if date_str in ("present", "current", "now"):
        from datetime import datetime
        now = datetime.now()
        return (now.year, now.month)

    # Try "Month Year" format
    for abbr, num in month_map.items():
        if date_str.startswith(abbr):
            year_match = re.search(r"(19|20)\d{2}", date_str)
            if year_match:
                return (int(year_match.group(0)), num)

    # Try "MM/YYYY" format
    slash_match = re.match(r"(\d{1,2})/(\d{4})", date_str)
    if slash_match:
        return (int(slash_match.group(2)), int(slash_match.group(1)))

    return None


# ─── Job Description Parser (Deterministic) ──────────────────────────────────


def parse_job_description(jd_text: str) -> "JobRequirements":
    """
    Parse a job description into structured requirements using regex/heuristics.
    Fallback when LLM is unavailable.
    """
    from models.schemas import JobRequirements

    text = jd_text.strip()
    lines = text.split("\n")

    # Extract title (first non-empty line, or line with common title patterns)
    title = None
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) < 100 and not line.startswith("-") and not line.startswith("•"):
            title = line
            break
    title = title or "Position"

    # Detect sections
    sections = _detect_jd_sections(text)

    # Extract skills from requirements section
    required_skills = []
    preferred_skills = []
    responsibilities = []
    min_experience = None
    education_req = None

    # Skills: scan for known skills in the requirements sections
    req_text = sections.get("requirements", "") + sections.get("qualifications", "")
    pref_text = sections.get("nice to have", "") + sections.get("preferred", "") + sections.get("bonus", "")
    resp_text = sections.get("responsibilities", "") + sections.get("duties", "")

    # If no sections found, use full text
    if not req_text and not pref_text:
        req_text = text

    # Extract skills from taxonomy
    text_lower = req_text.lower()
    for skill in SKILL_TAXONOMY:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            if skill not in [s.lower() for s in required_skills]:
                # Capitalize properly
                required_skills.append(_capitalize_skill(skill))

    pref_lower = pref_text.lower()
    for skill in SKILL_TAXONOMY:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, pref_lower):
            skill_cap = _capitalize_skill(skill)
            if skill_cap not in required_skills and skill_cap not in preferred_skills:
                preferred_skills.append(skill_cap)

    # Extract years of experience
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)', text, re.IGNORECASE)
    if exp_match:
        min_experience = int(exp_match.group(1))

    # Extract education
    edu_patterns = [
        r"(?:bachelor'?s?|b\.?s\.?|b\.?a\.?)\s+(?:degree\s+)?(?:in\s+)?(\w[\w\s,]+?)(?:\.|,|\n|or)",
        r"(?:master'?s?|m\.?s\.?|m\.?a\.?|ph\.?d\.?)\s+(?:degree\s+)?(?:in\s+)?(\w[\w\s,]+?)(?:\.|,|\n|or)",
        r"(?:degree|diploma)\s+in\s+(\w[\w\s,]+?)(?:\.|,|\n|or)",
    ]
    for pat in edu_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            education_req = m.group(0).strip().rstrip(".,")
            break

    if not education_req:
        if re.search(r"bachelor|b\.s\.|b\.a\.", text, re.IGNORECASE):
            education_req = "Bachelor's degree"
        elif re.search(r"master|m\.s\.|m\.a\.|ph\.d", text, re.IGNORECASE):
            education_req = "Master's degree or higher"

    # Extract responsibilities
    resp_lines = resp_text.split("\n") if resp_text else []
    for line in resp_lines:
        line = line.strip().lstrip("-•*").strip()
        if len(line) > 15:
            responsibilities.append(line)

    if not responsibilities:
        # Grab bullet points from anywhere
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("•"):
                clean = line.lstrip("-•*").strip()
                if len(clean) > 15 and clean not in [s for s in required_skills]:
                    responsibilities.append(clean)

    return JobRequirements(
        title=title,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        min_experience_years=min_experience,
        education_requirement=education_req,
        responsibilities=responsibilities[:10],
    )


def _detect_jd_sections(text: str) -> dict[str, str]:
    """Detect common JD section headers and extract their content."""
    section_patterns = [
        r"(?:requirements?|qualifications?|what (?:we|you) (?:need|require))",
        r"(?:nice to have|preferred|bonus|desirable)",
        r"(?:responsibilities|duties|what you'?ll do|role)",
        r"(?:about (?:the )?(?:role|position|job))",
    ]

    sections = {}
    lines = text.split("\n")
    current_section = None
    current_content = []

    for line in lines:
        stripped = line.strip().lower()
        # Check if this line is a section header
        is_header = False
        for pattern in section_patterns:
            if re.match(pattern, stripped) or (len(stripped) < 60 and re.search(pattern, stripped)):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = stripped
                current_content = []
                is_header = True
                break

        if not is_header and current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content)

    return sections


def _capitalize_skill(skill: str) -> str:
    """Capitalize a skill name properly."""
    # Known capitalizations
    caps = {
        "aws": "AWS", "gcp": "GCP", "sql": "SQL", "css": "CSS", "html": "HTML",
        "ci/cd": "CI/CD", "ci cd": "CI/CD", "rest": "REST", "restful": "RESTful",
        "graphql": "GraphQL", "nosql": "NoSQL", "mongodb": "MongoDB",
        "postgresql": "PostgreSQL", "mysql": "MySQL", "redis": "Redis",
        "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
        "terraform": "Terraform", "jenkins": "Jenkins", "ansible": "Ansible",
        "python": "Python", "java": "Java", "javascript": "JavaScript",
        "typescript": "TypeScript", "react": "React", "react.js": "React",
        "angular": "Angular", "vue": "Vue", "vue.js": "Vue.js",
        "node.js": "Node.js", "nodejs": "Node.js", "express": "Express",
        "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
        "spring boot": "Spring Boot", "spring": "Spring",
        "next.js": "Next.js", "nextjs": "Next.js",
        "go": "Go", "golang": "Go", "rust": "Rust", "ruby": "Ruby",
        "c++": "C++", "c#": "C#", "c": "C", "r": "R",
        "swift": "Swift", "kotlin": "Kotlin", "scala": "Scala",
        "azure": "Azure", "dynamodb": "DynamoDB", "elasticsearch": "Elasticsearch",
        "git": "Git", "linux": "Linux", "nginx": "Nginx",
        "pandas": "Pandas", "numpy": "NumPy", "tensorflow": "TensorFlow",
        "pytorch": "PyTorch", "scikit-learn": "scikit-learn",
        "amazon web services": "AWS", "google cloud": "GCP",
    }
    return caps.get(skill.lower(), skill.title())

