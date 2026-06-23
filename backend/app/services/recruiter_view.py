"""
Recruiter View Generator — Phase 6.
Produces a human-readable recruiter perspective on a candidate.
"""
from __future__ import annotations


def generate_recruiter_view(
    resume_data: dict,
    ats_result: dict,
    jd_intelligence: dict,
    gap_analysis: dict,
    quality_audit: dict,
) -> dict:
    """
    Return a recruiter-style summary of a candidate.

    Returns
    -------
    {
        strengths: list[str],
        weaknesses: list[str],
        interview_likelihood: str,     (HIGH | MEDIUM | LOW | VERY LOW)
        likelihood_reasoning: str,
        overall_impression: str,
        standout_factors: list[str],
        call_to_action: str,
    }
    """
    matched_skills = ats_result.get("matched_skills", [])
    matched_kws = ats_result.get("matched_keywords", [])

    strengths = _strengths(resume_data, ats_result, matched_skills, matched_kws)
    weaknesses = _weaknesses(gap_analysis, quality_audit, ats_result)
    likelihood, reasoning = _interview_likelihood(
        ats_result, gap_analysis, quality_audit, resume_data
    )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "interview_likelihood": likelihood,
        "likelihood_reasoning": reasoning,
        "overall_impression": _impression(ats_result.get("overall_score", 0), gap_analysis),
        "standout_factors": _standout(resume_data, matched_skills),
        "call_to_action": _cta(likelihood, gap_analysis, quality_audit),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strengths(resume_data, ats_result, matched_skills, matched_kws) -> list[str]:
    out: list[str] = []

    n_skills = len(matched_skills)
    if n_skills >= 6:
        out.append(f"Strong technical alignment — {n_skills} skills matched")
    elif n_skills >= 3:
        out.append(f"Good skill overlap — {n_skills} matching skills")

    kw_score = ats_result.get("keyword_score", 0)
    if kw_score >= 70:
        out.append("Excellent keyword match — high chance of passing automated ATS screening")
    elif kw_score >= 50:
        out.append("Good keyword coverage")

    years = resume_data.get("years_of_experience", 0)
    if years >= 3:
        out.append(f"Solid work experience ({years}+ years)")
    elif years >= 1:
        out.append("Has internship / work experience")

    edu = resume_data.get("education_level", 0)
    if edu >= 4:
        out.append("Advanced degree (Masters / PhD)")
    elif edu >= 3:
        out.append("Bachelor's degree in a relevant field")

    projects = resume_data.get("projects", [])
    if len(projects) >= 3:
        out.append(f"Strong project portfolio ({len(projects)} projects)")
    elif len(projects) >= 1:
        out.append("Has personal or academic projects demonstrating initiative")

    certs = resume_data.get("certifications", [])
    if certs:
        out.append(f"Holds {len(certs)} relevant certification(s)")

    sem = ats_result.get("semantic_score", 0)
    if sem >= 65:
        out.append("Resume language closely mirrors job description")

    return out[:6]


def _weaknesses(gap_analysis, quality_audit, ats_result) -> list[str]:
    out: list[str] = []

    critical = gap_analysis.get("critical_missing", [])
    important = gap_analysis.get("important_missing", [])

    if critical:
        sample = ", ".join(critical[:3])
        out.append(f"Missing critical skill(s): {sample}")
    if important:
        sample = ", ".join(important[:3])
        out.append(f"Missing preferred skill(s): {sample}")

    for issue in quality_audit.get("issues", []):
        if issue.get("severity") == "HIGH":
            out.append(issue["message"])
            if len(out) >= 5:
                break

    exp_score = ats_result.get("experience_score", 0)
    if exp_score < 40:
        out.append("Experience level significantly below job requirements")
    elif exp_score < 60:
        out.append("Experience level slightly below job requirements")

    kw_score = ats_result.get("keyword_score", 0)
    if kw_score < 30:
        out.append("Low keyword match — may be filtered by automated ATS")

    return out[:5]


def _interview_likelihood(ats_result, gap_analysis, quality_audit, resume_data) -> tuple[str, str]:
    base = ats_result.get("overall_score", 0)

    # Penalise critical gaps and quality issues
    crit_pen = min(20, len(gap_analysis.get("critical_missing", [])) * 4)
    qual_score = quality_audit.get("quality_score", 100)
    qual_pen = 0 if qual_score >= 70 else (15 if qual_score >= 50 else 25)

    # Small bonus when no experience but has strong projects
    proj_bonus = 0
    if resume_data.get("years_of_experience", 0) == 0 and len(resume_data.get("projects", [])) >= 2:
        proj_bonus = 5

    adjusted = max(0, min(100, base - crit_pen - qual_pen + proj_bonus))

    if adjusted >= 75:
        return (
            "HIGH",
            "Strong profile match. Likely to pass ATS screening and catch a recruiter's eye.",
        )
    if adjusted >= 55:
        return (
            "MEDIUM",
            "Reasonable match. May pass ATS but targeted tailoring will improve chances.",
        )
    if adjusted >= 35:
        return (
            "LOW",
            "Below-average match for this specific role. Address critical gaps before applying.",
        )
    return (
        "VERY LOW",
        "Poor fit for this specific role. Consider roles more aligned with your current profile.",
    )


def _impression(overall: float, gap_analysis: dict) -> str:
    sev = gap_analysis.get("severity_label", "LOW")
    if overall >= 80:
        return "Excellent candidate — strong fit for this role"
    if overall >= 65:
        return "Good candidate — a few targeted improvements would make this a top application"
    if overall >= 50:
        return "Decent candidate — notable gaps need addressing before applying"
    if overall >= 35:
        return "Below-average match — significant rework needed for this specific role"
    return "Poor fit for this specific role — consider positions better aligned with your profile"


def _standout(resume_data: dict, matched_skills: list) -> list[str]:
    factors: list[str] = []
    if len(matched_skills) >= 8:
        factors.append(f"Broad tech stack ({len(matched_skills)} matched skills)")
    if resume_data.get("github"):
        factors.append("GitHub profile linked — work can be verified")
    if resume_data.get("linkedin"):
        factors.append("LinkedIn profile provided")
    certs = resume_data.get("certifications", [])
    if certs:
        factors.append(f"Certifications: {', '.join(certs[:2])}")
    if len(resume_data.get("projects", [])) >= 4:
        factors.append("Impressive project portfolio")
    return factors[:4]


def _cta(likelihood: str, gap_analysis: dict, quality_audit: dict) -> str:
    critical = gap_analysis.get("critical_missing", [])
    qual_score = quality_audit.get("quality_score", 0)

    if likelihood == "HIGH":
        return "Apply now — strong match. Submit within 24 hours for best visibility."
    if likelihood == "MEDIUM":
        actions: list[str] = []
        if critical:
            actions.append(f"address '{critical[0]}' gap in your cover letter or resume")
        if qual_score < 60:
            actions.append("improve resume quality score")
        return "Apply after improvements: " + ("; ".join(actions) or "minor polish recommended") + "."
    actions = []
    if critical:
        actions.append(f"gain exposure to {', '.join(critical[:2])}")
    actions.append("target entry-level or internship roles to build track record")
    return "Before applying: " + "; ".join(actions) + "."
