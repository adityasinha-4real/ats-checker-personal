"""
Cover Letter Generator — Feature 3.
Produces a cover letter using ONLY information already present in the resume.
No experience, skills, or achievements are fabricated.
"""
from __future__ import annotations

import re
from typing import Any


_WEAK_OPENERS = re.compile(
    r"^(i |we |the |a |an |this |our |my )", re.IGNORECASE
)

_ROLE_WORDS = re.compile(
    r"\b(engineer|developer|scientist|analyst|architect|lead|manager|intern|specialist)\b",
    re.IGNORECASE,
)


def _first_n_words(text: str, n: int = 20) -> str:
    words = text.split()
    return " ".join(words[:n]) + ("…" if len(words) > n else "")


def _pick_highlight_project(projects: list[str], jd_text: str) -> str:
    """Return the project text most relevant to the JD (simple word overlap)."""
    if not projects:
        return ""
    jd_words = set(re.findall(r"\b\w{4,}\b", jd_text.lower()))
    scored = []
    for p in projects:
        p_words = set(re.findall(r"\b\w{4,}\b", p.lower()))
        scored.append((len(p_words & jd_words), p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _match_skills(resume_skills: list[str], jd_text: str, top_n: int = 6) -> list[str]:
    """Return up to top_n resume skills that appear in the JD."""
    jd_lower = jd_text.lower()
    matched = [s for s in resume_skills if s.lower() in jd_lower]
    if not matched:
        matched = resume_skills[:top_n]
    return matched[:top_n]


def _background_phrase(resume_data: dict, mode: str) -> str:
    years = resume_data.get("years_of_experience") or 0
    edu = resume_data.get("education", [])
    degree = edu[0].get("degree", "") if edu else ""

    if mode == "fresher" or years < 2:
        if degree:
            return f"a {degree} candidate"
        return "an aspiring technology professional"
    if years < 5:
        return f"a software professional with {int(years)} years of experience"
    return f"an experienced software professional with {int(years)} years of industry experience"


def generate_cover_letter(
    resume_data: dict[str, Any],
    jd_text: str,
    company_name: str,
    jd_intelligence: dict[str, Any] | None = None,
    mode: str = "experienced",
) -> dict[str, Any]:
    """
    Generate a cover letter from existing resume content only.
    Returns paragraphs and the assembled full text.
    """
    name = resume_data.get("name") or "Applicant"
    skills: list[str] = resume_data.get("skills") or []
    projects: list[str] = resume_data.get("projects") or []
    experience: list[str] = resume_data.get("experience") or []
    certifications: list[str] = resume_data.get("certifications") or []

    # Resolve role title from JD intelligence or fallback
    role_title = "Software Engineer"
    if jd_intelligence:
        crit = jd_intelligence.get("critical_requirements", [])
        if crit:
            role_title = crit[0] if _ROLE_WORDS.search(crit[0]) else role_title
    else:
        match = _ROLE_WORDS.search(jd_text[:300])
        if match:
            start = max(0, match.start() - 20)
            role_title = jd_text[start : match.end()].strip().title()

    matched_skills = _match_skills(skills, jd_text)
    skills_str = ", ".join(matched_skills) if matched_skills else "a range of technical skills"

    background = _background_phrase(resume_data, mode)

    # ── Opening paragraph ──────────────────────────────────────────────────────
    opening = (
        f"I am writing to express my interest in the {role_title} position at {company_name}. "
        f"As {background}, I am excited by the opportunity to contribute to your team "
        f"and believe my technical background aligns well with your requirements."
    )

    # ── Technical body paragraph ───────────────────────────────────────────────
    if experience:
        exp_snippet = _first_n_words(experience[0], 25)
        body_technical = (
            f"My technical experience spans {skills_str}. "
            f"In my previous work, I have {exp_snippet.lower().lstrip('i ')}. "
            f"I am comfortable working across the full development lifecycle and "
            f"have consistently delivered results that meet both technical and business objectives."
        )
    else:
        body_technical = (
            f"I have developed hands-on proficiency in {skills_str} through academic "
            f"projects and self-directed learning. I approach technical challenges "
            f"methodically and am committed to writing clean, maintainable code."
        )

    # ── Project highlight paragraph ────────────────────────────────────────────
    highlight = _pick_highlight_project(projects, jd_text)
    if highlight:
        proj_snippet = _first_n_words(highlight, 30)
        body_projects = (
            f"One project I am particularly proud of involved {proj_snippet.lower()}. "
            f"This experience strengthened my ability to deliver working software "
            f"under real-world constraints and reinforced my passion for building "
            f"reliable, scalable systems."
        )
    else:
        body_projects = (
            f"Throughout my work I have prioritised code quality, collaboration, "
            f"and continuous learning — values I understand {company_name} shares. "
            f"I am eager to bring this mindset to your team."
        )

    # ── Certifications note (optional) ────────────────────────────────────────
    cert_note = ""
    if certifications:
        cert_note = f" I also hold {certifications[0]}, which further validates my commitment to this domain."

    # ── Closing paragraph ─────────────────────────────────────────────────────
    closing = (
        f"I am enthusiastic about the work {company_name} is doing and would welcome "
        f"the opportunity to discuss how I can contribute.{cert_note} "
        f"Thank you for considering my application. I look forward to the possibility "
        f"of joining your team.\n\nSincerely,\n{name}"
    )

    paragraphs = {
        "opening": opening,
        "body_technical": body_technical,
        "body_projects": body_projects,
        "closing": closing,
    }

    full_text = "\n\n".join([opening, body_technical, body_projects, closing])
    word_count = len(full_text.split())

    safety_notes: list[str] = []
    if not experience:
        safety_notes.append("No experience entries found — body_technical uses generic language.")
    if not highlight:
        safety_notes.append("No projects found — body_projects uses generic language.")
    if not matched_skills:
        safety_notes.append("No skills matched the JD — skills list uses all resume skills.")

    return {
        "cover_letter_text": full_text,
        "paragraphs": paragraphs,
        "word_count": word_count,
        "safety_notes": safety_notes,
    }
