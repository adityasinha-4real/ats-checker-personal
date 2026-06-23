"""
Market Analyzer — Feature 6.
Aggregates skill demand across multiple JDs and identifies profile gaps.
"""
from __future__ import annotations

from collections import Counter
from loguru import logger
from app.services.nlp_engine import extract_skills_from_text, TECH_SKILLS


_CATEGORY_MAP: dict[str, str] = {
    "languages": "programming_languages",
    "frontend": "frameworks",
    "backend": "frameworks",
    "mobile": "frameworks",
    "databases": "databases",
    "cloud": "cloud",
    "devops": "tools",
    "ml_ai": "frameworks",
    "tools": "tools",
    "concepts": "concepts",
    "data_engineering": "tools",
    "security": "concepts",
}

_SKILL_TO_CATEGORY: dict[str, str] = {}
for _cat, _skills in TECH_SKILLS.items():
    _mapped = _CATEGORY_MAP.get(_cat, "tools")
    for _s in _skills:
        _SKILL_TO_CATEGORY[_s.lower()] = _mapped


def analyze_market(
    jd_texts: list[str],
    resume_skills: list[str] | None = None,
) -> dict:
    """
    Analyze multiple JDs to find most in-demand skills.

    Args:
        jd_texts: Job description text strings.
        resume_skills: Resume skills list (optional) — used to compute gaps.
    """
    if not jd_texts:
        return _empty_result()

    n = len(jd_texts)
    skill_jd_sets: dict[str, set[int]] = {}

    for idx, jd_text in enumerate(jd_texts):
        try:
            for skill in extract_skills_from_text(jd_text):
                skill_jd_sets.setdefault(skill.lower(), set()).add(idx)
        except Exception as e:
            logger.warning(f"Market analyzer error on JD {idx}: {e}")

    freq: Counter = Counter({skill: len(jd_set) for skill, jd_set in skill_jd_sets.items()})

    top_languages: list[dict] = []
    top_frameworks: list[dict] = []
    top_tools: list[dict] = []
    top_cloud: list[dict] = []
    top_databases: list[dict] = []
    top_concepts: list[dict] = []

    for skill, count in freq.most_common(100):
        cat = _SKILL_TO_CATEGORY.get(skill.lower(), "tools")
        entry = {"skill": skill, "count": count, "percentage": round(count / n * 100)}
        if cat == "programming_languages":
            top_languages.append(entry)
        elif cat == "frameworks":
            top_frameworks.append(entry)
        elif cat == "cloud":
            top_cloud.append(entry)
        elif cat == "databases":
            top_databases.append(entry)
        elif cat == "concepts":
            top_concepts.append(entry)
        else:
            top_tools.append(entry)

    top_skills = [
        {"skill": s, "count": c, "percentage": round(c / n * 100)}
        for s, c in freq.most_common(20)
    ]

    missing_from_profile: list[dict] = []
    if resume_skills is not None:
        resume_set = {s.lower() for s in resume_skills}
        for skill, count in freq.most_common(30):
            if skill.lower() not in resume_set:
                missing_from_profile.append({
                    "skill": skill,
                    "count": count,
                    "percentage": round(count / n * 100),
                    "category": _SKILL_TO_CATEGORY.get(skill.lower(), "tools"),
                })

    return {
        "jd_count": n,
        "total_unique_skills": len(skill_jd_sets),
        "top_skills": top_skills,
        "top_languages": top_languages[:10],
        "top_frameworks": top_frameworks[:10],
        "top_tools": top_tools[:10],
        "top_cloud": top_cloud[:10],
        "top_databases": top_databases[:8],
        "top_concepts": top_concepts[:8],
        "missing_from_profile": missing_from_profile[:15],
        "profile_provided": resume_skills is not None,
    }


def _empty_result() -> dict:
    return {
        "jd_count": 0,
        "total_unique_skills": 0,
        "top_skills": [],
        "top_languages": [],
        "top_frameworks": [],
        "top_tools": [],
        "top_cloud": [],
        "top_databases": [],
        "top_concepts": [],
        "missing_from_profile": [],
        "profile_provided": False,
    }
