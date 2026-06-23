"""
Resume Quality Auditor — Phase 8.
Checks a parsed resume for common quality issues and emits a 0-100 score.
"""
from __future__ import annotations

import re

STRONG_VERBS = {
    "developed", "built", "implemented", "designed", "architected",
    "optimized", "optimised", "improved", "deployed", "integrated",
    "created", "led", "delivered", "automated", "analyzed", "analysed",
    "configured", "migrated", "refactored", "scaled", "launched",
    "engineered", "established", "reduced", "increased", "mentored",
    "executed", "spearheaded", "streamlined", "accelerated",
    "coordinated", "produced", "drove",
}

WEAK_PHRASES = [
    "worked on", "helped with", "assisted with", "was responsible for",
    "helped to", "assisted in", "participated in", "involved in",
    "contributed to", "responsible for",
]

METRIC_RE = re.compile(
    r"(\d+%|\$[\d,]+|\d+[xX]|\b\d+k\+?|\d[\d,]*\s*(?:users?|requests?|transactions?|"
    r"records?|lines?|hours?|days?|minutes?))",
    re.IGNORECASE,
)


def audit_resume(resume_data: dict) -> dict:
    """
    Run a quality audit on parsed resume data.

    Returns
    -------
    {
        quality_score      : int (0-100),
        quality_label      : str,
        issues             : list[{category, severity, message, fix}],
        positive_signals   : list[str],
        high_severity_count: int,
        ...
    }
    """
    raw = resume_data.get("raw_text", "") or ""
    raw_lower = raw.lower()
    issues: list[dict] = []

    # ── Contact info ─────────────────────────────────────────────────────────
    if not resume_data.get("emails"):
        issues.append(_issue("contact", "HIGH", "Missing email address", "Add a professional email address"))
    if not resume_data.get("phones"):
        issues.append(_issue("contact", "MEDIUM", "Missing phone number", "Add your phone number"))
    if not resume_data.get("linkedin"):
        issues.append(_issue("contact", "LOW", "No LinkedIn URL found", "Add linkedin.com/in/yourname"))
    if not resume_data.get("github"):
        issues.append(_issue(
            "contact", "LOW",
            "No GitHub profile found — important for software engineering roles",
            "Add github.com/yourname",
        ))

    # ── Section structure ─────────────────────────────────────────────────────
    sections = resume_data.get("sections_detected", [])
    if "summary" not in sections:
        issues.append(_issue(
            "structure", "MEDIUM",
            "No professional summary/objective section",
            "Add a 2-3 sentence summary tailored to the target role",
        ))
    if "skills" not in sections and not resume_data.get("skills"):
        issues.append(_issue(
            "structure", "HIGH",
            "No Skills section found — critical for ATS keyword matching",
            "Add a dedicated Skills section with your tech skills",
        ))
    if "projects" not in sections and not resume_data.get("projects"):
        issues.append(_issue(
            "structure", "HIGH",
            "No Projects section — crucial for fresher/student applications",
            "Add 2-4 projects with tech stack, GitHub links, and outcomes",
        ))
    if "experience" not in sections and resume_data.get("years_of_experience", 0) == 0:
        issues.append(_issue(
            "structure", "MEDIUM",
            "No Work Experience section detected",
            "Add internships, freelance work, or part-time roles",
        ))

    # ── Content length ────────────────────────────────────────────────────────
    wc = resume_data.get("word_count", 0)
    if wc < 150:
        issues.append(_issue(
            "content", "HIGH",
            f"Resume is very short ({wc} words) — insufficient detail",
            "Expand experience, project, and skills sections",
        ))
    elif wc > 1500:
        issues.append(_issue(
            "content", "MEDIUM",
            f"Resume is long ({wc} words) — consider condensing to 1-2 pages",
            "Remove outdated or irrelevant content",
        ))

    # ── Action verbs ──────────────────────────────────────────────────────────
    has_strong = any(v in raw_lower for v in STRONG_VERBS)
    has_weak = any(raw_lower.find(p) != -1 for p in WEAK_PHRASES)

    if not has_strong:
        issues.append(_issue(
            "language", "HIGH",
            "No strong action verbs detected",
            "Use verbs like: Developed, Built, Implemented, Optimized, Led, Deployed",
        ))
    elif has_weak:
        issues.append(_issue(
            "language", "MEDIUM",
            "Weak verbs detected (e.g., 'worked on', 'was responsible for')",
            "Replace with action verbs: Developed, Built, Configured …",
        ))

    # ── Metrics / quantification ─────────────────────────────────────────────
    has_metrics = bool(METRIC_RE.search(raw))
    if not has_metrics:
        issues.append(_issue(
            "content", "MEDIUM",
            "No quantifiable achievements found",
            "Add numbers: 'Reduced load time by 40%', 'Served 10K+ users', 'Cut build time by 3 min'",
        ))

    # ── Weak project descriptions ─────────────────────────────────────────────
    projects = resume_data.get("projects", [])
    short_idx: list[int] = []
    for i, proj in enumerate(projects):
        text = proj if isinstance(proj, str) else proj.get("description", "")
        if len((text or "").split()) < 15:
            short_idx.append(i + 1)
    if short_idx:
        issues.append(_issue(
            "content", "MEDIUM",
            f"Project(s) {short_idx} have very short descriptions",
            "Expand: include tech stack, what the project does, challenges, and outcomes",
        ))

    score = _compute_score(issues, resume_data)
    positives = _positive_signals(resume_data, has_strong, has_metrics)

    return {
        "quality_score": score,
        "quality_label": _label(score),
        "issues": issues,
        "positive_signals": positives,
        "high_severity_count": sum(1 for i in issues if i["severity"] == "HIGH"),
        "medium_severity_count": sum(1 for i in issues if i["severity"] == "MEDIUM"),
        "low_severity_count": sum(1 for i in issues if i["severity"] == "LOW"),
        "issue_count": len(issues),
    }


def _issue(category: str, severity: str, message: str, fix: str) -> dict:
    return {"category": category, "severity": severity, "message": message, "fix": fix}


def _compute_score(issues: list[dict], resume_data: dict) -> int:
    score = 100
    for issue in issues:
        score -= {"HIGH": 15, "MEDIUM": 8, "LOW": 3}.get(issue["severity"], 0)
    # Bonuses for positive signals
    if resume_data.get("github"):
        score += 5
    if resume_data.get("linkedin"):
        score += 3
    if len(resume_data.get("projects", [])) >= 3:
        score += 5
    if resume_data.get("certifications"):
        score += 4
    return max(0, min(100, score))


def _label(score: int) -> str:
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "GOOD"
    if score >= 50:
        return "AVERAGE"
    if score >= 30:
        return "BELOW AVERAGE"
    return "POOR"


def _positive_signals(resume_data: dict, has_strong: bool, has_metrics: bool) -> list[str]:
    out: list[str] = []
    if has_strong:
        out.append("Uses strong action verbs")
    if has_metrics:
        out.append("Contains quantifiable achievements")
    if resume_data.get("github"):
        out.append("GitHub profile included")
    if resume_data.get("linkedin"):
        out.append("LinkedIn profile included")
    n_proj = len(resume_data.get("projects", []))
    if n_proj >= 2:
        out.append(f"{n_proj} project(s) listed")
    if resume_data.get("certifications"):
        out.append(f"{len(resume_data['certifications'])} certification(s) found")
    if resume_data.get("emails"):
        out.append("Email address present")
    return out
