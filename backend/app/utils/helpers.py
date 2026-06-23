import re
import uuid
from pathlib import Path
from loguru import logger


def generate_unique_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


def get_file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()


def extract_emails(text: str) -> list[str]:
    pattern = r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    return list(set(re.findall(pattern, text)))


def extract_phones(text: str) -> list[str]:
    pattern = r"(?:\+?\d{1,3}[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"
    return list(set(re.findall(pattern, text)))


def extract_urls(text: str) -> list[str]:
    pattern = r"https?://[^\s]+"
    return list(set(re.findall(pattern, text)))


def extract_linkedin(text: str) -> str | None:
    pattern = r"linkedin\.com/in/[\w\-]+"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def extract_github(text: str) -> str | None:
    pattern = r"github\.com/[\w\-]+"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def extract_years_of_experience(text: str) -> int:
    """
    Extract total years of experience from resume text.
    Looks for patterns like date ranges in work experience.
    """
    patterns = [
        r"(\d{4})\s*[-–]\s*(present|current|now|\d{4})",
        r"(\d{1,2})\+?\s*years?\s*(?:of\s+)?(?:work\s+)?experience",
    ]
    total_years = 0
    current_year = 2024

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple) and len(match) == 2:
                start, end = match
                try:
                    start_year = int(start)
                    end_year = current_year if end.lower() in ("present", "current", "now") else int(end)
                    duration = max(0, end_year - start_year)
                    total_years += duration
                except ValueError:
                    pass

    if total_years == 0:
        for pattern in patterns[1:]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    total_years = int(match.group(1))
                except (ValueError, IndexError):
                    pass

    return min(total_years, 40)


SECTION_HEADERS = {
    "experience": ["experience", "work experience", "employment", "work history", "professional experience", "career history"],
    "education": ["education", "academic background", "academic qualifications", "educational background", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tools", "competencies", "expertise"],
    "projects": ["projects", "personal projects", "academic projects", "key projects", "portfolio"],
    "certifications": ["certifications", "certificates", "licenses", "awards", "achievements"],
    "summary": ["summary", "objective", "profile", "about me", "professional summary", "career objective"],
}


def detect_section(line: str) -> str | None:
    line_lower = line.lower().strip()
    for section, keywords in SECTION_HEADERS.items():
        for kw in keywords:
            if line_lower == kw or line_lower.startswith(kw + ":"):
                return section
    return None


def extract_sections(text: str) -> dict[str, str]:
    lines = text.split("\n")
    sections: dict[str, list[str]] = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        section = detect_section(line)
        if section:
            current_section = section
            sections[current_section] = []
        else:
            sections.setdefault(current_section, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def normalize_score(score: float) -> float:
    return max(0.0, min(100.0, round(score, 2)))
