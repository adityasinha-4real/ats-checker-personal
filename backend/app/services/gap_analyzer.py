"""
Critical Gap Analysis — Phase 2.
Categorises missing skills/keywords into Critical / Important / Optional
and computes a severity score that feeds back into the ATS result.
"""
from __future__ import annotations

from rapidfuzz import fuzz
from app.services.nlp_engine import normalize_skill

FUZZY_THRESHOLD = 80


def _skill_present(skill: str, resume_skill_set: set[str], resume_text_lower: str) -> bool:
    """Return True if skill can be found in the resume by exact, alias, or fuzzy match."""
    norm = normalize_skill(skill)
    if norm in resume_skill_set:
        return True
    if skill.lower() in resume_text_lower:
        return True
    for rs in resume_skill_set:
        if fuzz.token_set_ratio(norm, rs) >= FUZZY_THRESHOLD:
            return True
    return False


def analyze_gaps(
    resume_data: dict,
    jd_intelligence: dict,
    ats_result: dict,
) -> dict:
    """
    Classify missing skills into Critical / Important / Optional.

    Parameters
    ----------
    resume_data     : parsed resume dict
    jd_intelligence : output of classify_jd()
    ats_result      : output of run_ats_analysis()

    Returns
    -------
    {
        critical_missing   : list[str],
        important_missing  : list[str],
        optional_missing   : list[str],
        severity_score     : int  (0-100, higher = worse),
        severity_label     : str  (LOW | MEDIUM | HIGH),
        score_impact       : int  (estimated ATS score reduction from gaps),
        critical_count     : int,
        important_count    : int,
        optional_count     : int,
        summary            : str,
    }
    """
    resume_skills = {normalize_skill(s) for s in resume_data.get("skills", [])}
    resume_text = (resume_data.get("raw_text", "") or "").lower()

    critical_reqs = jd_intelligence.get("critical_requirements", [])
    preferred_reqs = jd_intelligence.get("preferred_requirements", [])

    # Already-categorised missing from basic ATS pass
    already_missing = set(ats_result.get("missing_skills", []))

    critical_missing: list[str] = []
    important_missing: list[str] = []
    optional_missing: list[str] = []

    for skill in critical_reqs:
        if not _skill_present(skill, resume_skills, resume_text):
            critical_missing.append(skill)

    for skill in preferred_reqs:
        if not _skill_present(skill, resume_skills, resume_text):
            important_missing.append(skill)

    # Anything the ATS scorer flagged but we haven't categorised yet → optional
    categorised = set(critical_missing) | set(important_missing)
    for skill in already_missing:
        if skill not in categorised and not _skill_present(skill, resume_skills, resume_text):
            optional_missing.append(skill)

    # ── Severity computation ────────────────────────────────────────────────
    crit_ratio = len(critical_missing) / max(len(critical_reqs), 1)
    pref_ratio = len(important_missing) / max(len(preferred_reqs), 1)

    severity_score = int(min(100, crit_ratio * 70 + pref_ratio * 30))

    if severity_score >= 60:
        severity_label = "HIGH"
    elif severity_score >= 30:
        severity_label = "MEDIUM"
    else:
        severity_label = "LOW"

    # Estimated ATS point penalty from critical gaps (max ~25 pts)
    score_impact = min(25, round(crit_ratio * 25))

    return {
        "critical_missing": critical_missing[:15],
        "important_missing": important_missing[:15],
        "optional_missing": optional_missing[:15],
        "severity_score": severity_score,
        "severity_label": severity_label,
        "score_impact": score_impact,
        "critical_count": len(critical_missing),
        "important_count": len(important_missing),
        "optional_count": len(optional_missing),
        "summary": _build_summary(critical_missing, important_missing, severity_label),
    }


def _build_summary(critical: list, important: list, severity: str) -> str:
    if not critical and not important:
        return "Your resume covers the key requirements for this role."
    parts = []
    if critical:
        sample = ", ".join(critical[:3])
        parts.append(f"{len(critical)} critical skill(s) missing: {sample}")
    if important:
        sample = ", ".join(important[:3])
        parts.append(f"{len(important)} preferred skill(s) missing: {sample}")
    prefix = {
        "HIGH": "Significant gaps detected. ",
        "MEDIUM": "Some gaps detected. ",
        "LOW": "Minor gaps detected. ",
    }.get(severity, "")
    return prefix + "; ".join(parts) + "."
