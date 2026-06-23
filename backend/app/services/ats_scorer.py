"""
ATS scoring engine.

Weights:
  keyword_score    35%
  skills_score     25%
  experience_score 15%
  education_score  10%
  semantic_score   15%
"""
from __future__ import annotations

import re
from loguru import logger
from rapidfuzz import fuzz, process

from app.config import settings
from app.services.nlp_engine import (
    extract_jd_keywords,
    extract_skills_from_text,
    extract_education_level,
    compute_semantic_similarity,
    normalize_skill,
    EDUCATION_LEVELS,
)
from app.utils.helpers import (
    extract_years_of_experience,
    normalize_score,
    extract_sections,
)

FUZZY_THRESHOLD = 80


def _fuzzy_match(keyword: str, text: str) -> bool:
    """Check if keyword approximately appears in text."""
    kw = keyword.lower()
    if kw in text:
        return True
    words = text.split()
    chunks = []
    kw_words = kw.split()
    n = len(kw_words)
    for i in range(len(words) - n + 1):
        chunks.append(" ".join(words[i:i + n]))
    if not chunks:
        return False
    best = process.extractOne(kw, chunks, scorer=fuzz.token_set_ratio)
    return best is not None and best[1] >= FUZZY_THRESHOLD


def score_keywords(resume_text: str, jd_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    """
    Keyword match score (0-100).
    Uses exact + fuzzy matching.
    """
    if not jd_keywords:
        return 50.0, [], []

    resume_lower = resume_text.lower()
    matched: list[str] = []
    missing: list[str] = []

    for kw in jd_keywords:
        if _fuzzy_match(kw, resume_lower):
            matched.append(kw)
        else:
            missing.append(kw)

    score = (len(matched) / len(jd_keywords)) * 100
    return normalize_score(score), matched, missing


def score_skills(resume_skills: list[str], jd_skills: list[str]) -> tuple[float, list[str], list[str]]:
    """
    Skills match score (0-100).
    Normalises both lists before comparison (handles aliases).
    """
    if not jd_skills:
        return 50.0, [], []

    norm_resume = {normalize_skill(s) for s in resume_skills}
    matched: list[str] = []
    missing: list[str] = []

    for skill in jd_skills:
        ns = normalize_skill(skill)
        if ns in norm_resume:
            matched.append(skill)
        else:
            found = False
            for rs in norm_resume:
                ratio = fuzz.token_set_ratio(ns, rs)
                if ratio >= FUZZY_THRESHOLD:
                    found = True
                    break
            if found:
                matched.append(skill)
            else:
                missing.append(skill)

    score = (len(matched) / len(jd_skills)) * 100
    return normalize_score(score), matched, missing


def score_experience(resume_years: int, jd_text: str) -> float:
    """
    Experience match score (0-100).
    Extracts required years from JD and compares with resume.
    """
    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:work\s+)?(?:relevant\s+)?experience",
        r"minimum\s+(?:of\s+)?(\d+)\s*years?",
        r"at\s+least\s+(\d+)\s*years?",
        r"(\d+)\s*[-–]\s*\d+\s*years?",
        r"(\d+)\+\s*years?",
    ]
    required_years = 0
    for pattern in patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            try:
                required_years = int(match.group(1))
                break
            except (ValueError, IndexError):
                pass

    if required_years == 0:
        return 70.0

    if resume_years >= required_years:
        return 100.0
    elif resume_years >= required_years * 0.75:
        return 80.0
    elif resume_years >= required_years * 0.5:
        return 60.0
    elif resume_years >= required_years * 0.25:
        return 40.0
    else:
        return 20.0


def score_education(resume_level: int, jd_text: str) -> float:
    """
    Education match score (0-100).
    Extracts required degree from JD and compares with resume.
    """
    jd_lower = jd_text.lower()
    required_level = 0
    for degree, level in EDUCATION_LEVELS.items():
        if degree in jd_lower:
            required_level = max(required_level, level)

    if required_level == 0:
        return 80.0

    if resume_level >= required_level:
        return 100.0
    elif resume_level == required_level - 1:
        return 65.0
    elif resume_level == required_level - 2:
        return 40.0
    else:
        return 20.0


def generate_suggestions(
    missing_keywords: list[str],
    missing_skills: list[str],
    resume_data: dict,
    jd_text: str,
) -> list[str]:
    """Generate actionable improvement suggestions."""
    suggestions: list[str] = []
    sections = resume_data.get("sections_detected", [])

    if missing_skills:
        top_missing = missing_skills[:5]
        suggestions.append(f"Add these skills to your resume: {', '.join(top_missing)}")

    if missing_keywords:
        top_kws = missing_keywords[:8]
        suggestions.append(
            f"Include these keywords from the job description: {', '.join(top_kws)}"
        )

    if "summary" not in sections:
        suggestions.append(
            "Add a professional summary/objective tailored to this job description"
        )

    if "projects" not in sections:
        suggestions.append(
            "Add a Projects section with relevant personal/academic projects"
        )

    if "certifications" not in sections and any(
        kw in jd_text.lower() for kw in ["certified", "certification", "aws", "azure", "google cloud"]
    ):
        suggestions.append(
            "Consider adding relevant certifications (AWS, Azure, Google Cloud, etc.)"
        )

    word_count = resume_data.get("word_count", 0)
    if word_count < 200:
        suggestions.append(
            "Your resume appears short. Add more detail to your experience and projects sections"
        )
    elif word_count > 1200:
        suggestions.append(
            "Consider condensing your resume to 1-2 pages for ATS optimisation"
        )

    resume_text = resume_data.get("raw_text", "").lower()
    action_verbs = ["developed", "built", "implemented", "led", "designed", "optimised", "improved"]
    if not any(v in resume_text for v in action_verbs):
        suggestions.append(
            "Use strong action verbs (Developed, Built, Led, Implemented) to describe your experience"
        )

    if "%" not in resume_text and "metric" not in resume_text:
        suggestions.append(
            "Add quantifiable achievements (e.g., 'Improved performance by 40%') to strengthen your impact"
        )

    return suggestions[:10]


_FRESHER_WEIGHTS = {
    "keyword": 0.25,
    "skills": 0.40,
    "experience": 0.05,
    "education": 0.15,
    "semantic": 0.15,
}
_STANDARD_WEIGHTS = {
    "keyword": settings.keyword_weight,
    "skills": settings.skills_weight,
    "experience": settings.experience_weight,
    "education": settings.education_weight,
    "semantic": settings.semantic_weight,
}


def run_ats_analysis(resume_data: dict, jd_text: str, fresher_mode: bool = False) -> dict:
    """
    Full ATS analysis pipeline.
    fresher_mode=True: boosts skills/education weights, reduces experience weight.
    """
    resume_text = resume_data.get("raw_text", "")
    resume_skills = resume_data.get("skills", [])
    resume_edu_level = resume_data.get("education_level", 0)
    resume_years = resume_data.get("years_of_experience", 0)

    jd_keywords = extract_jd_keywords(jd_text)
    jd_skills = extract_skills_from_text(jd_text)
    jd_edu_level = extract_education_level(jd_text)

    kw_score, matched_kws, missing_kws = score_keywords(resume_text, jd_keywords)
    sk_score, matched_skills, missing_skills = score_skills(resume_skills, jd_skills)
    exp_score = score_experience(resume_years, jd_text)
    edu_score = score_education(resume_edu_level, jd_text)

    try:
        sem_score = compute_semantic_similarity(resume_text[:3000], jd_text[:3000])
    except Exception as e:
        logger.warning(f"Semantic similarity failed: {e}")
        sem_score = 50.0

    weights = _FRESHER_WEIGHTS if fresher_mode else _STANDARD_WEIGHTS

    overall = (
        kw_score * weights["keyword"]
        + sk_score * weights["skills"]
        + exp_score * weights["experience"]
        + edu_score * weights["education"]
        + sem_score * weights["semantic"]
    )

    suggestions = generate_suggestions(missing_kws, missing_skills, resume_data, jd_text)

    return {
        "overall_score": normalize_score(overall),
        "keyword_score": normalize_score(kw_score),
        "skills_score": normalize_score(sk_score),
        "experience_score": normalize_score(exp_score),
        "education_score": normalize_score(edu_score),
        "semantic_score": normalize_score(sem_score),
        "missing_keywords": missing_kws[:30],
        "missing_skills": missing_skills[:20],
        "matched_keywords": matched_kws[:30],
        "matched_skills": matched_skills[:20],
        "suggestions": suggestions,
        "fresher_mode": fresher_mode,
        "details": {
            "jd_keywords_count": len(jd_keywords),
            "jd_skills_count": len(jd_skills),
            "resume_skills_count": len(resume_skills),
            "resume_years_experience": resume_years,
            "resume_education_level": resume_edu_level,
            "jd_education_level": jd_edu_level,
            "jd_required_years": _extract_required_years(jd_text),
            "resume_word_count": resume_data.get("word_count", 0),
            "weights_used": "fresher" if fresher_mode else "standard",
        },
    }


def _extract_required_years(jd_text: str) -> int:
    pattern = r"(\d+)\+?\s*years?"
    match = re.search(pattern, jd_text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return 0
