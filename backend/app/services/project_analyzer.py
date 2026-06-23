"""
Project Relevance Analyzer — Phase 4.
Scores each project in the resume against the job description.
"""
from __future__ import annotations

import re
from loguru import logger
from rapidfuzz import fuzz

from app.services.nlp_engine import (
    extract_skills_from_text,
    extract_jd_keywords,
    compute_semantic_similarity,
)


# ── Project extraction ────────────────────────────────────────────────────────

_PROJECT_HEADER_RE = re.compile(
    r"^(?:PROJECTS?|PERSONAL\s+PROJECTS?|ACADEMIC\s+PROJECTS?|SIDE\s+PROJECTS?)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

_PROJECT_ENTRY_RE = re.compile(
    r"(?:^|\n)([A-Z][^\n]{3,60})\n((?:(?!^[A-Z][^\n]{3,60}\n)[\s\S])*)",
    re.MULTILINE,
)


def _extract_project_blocks(resume_data: dict) -> list[dict]:
    """Extract individual project blocks with name + text."""
    projects_raw = resume_data.get("projects", [])
    raw_text = resume_data.get("raw_text", "") or ""
    blocks: list[dict] = []

    if projects_raw:
        for i, proj in enumerate(projects_raw):
            if isinstance(proj, str) and len(proj.strip()) > 10:
                # Try to split name from body
                lines = proj.strip().splitlines()
                name = lines[0].strip() if lines else f"Project {i + 1}"
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else proj
                blocks.append({"index": i, "name": name, "text": body or proj})
            elif isinstance(proj, dict):
                blocks.append({
                    "index": i,
                    "name": proj.get("name", f"Project {i + 1}"),
                    "text": proj.get("description", proj.get("text", "")),
                })

    if not blocks and raw_text:
        # Attempt regex extraction from raw text
        proj_section = ""
        m = _PROJECT_HEADER_RE.search(raw_text)
        if m:
            proj_section = raw_text[m.end():]
            # Cut off at next major section
            next_section = re.search(
                r"\n(?:EXPERIENCE|EDUCATION|SKILLS|CERTIFICATIONS|AWARDS)\s*\n",
                proj_section,
                re.IGNORECASE,
            )
            if next_section:
                proj_section = proj_section[: next_section.start()]

        if proj_section:
            for i, match in enumerate(_PROJECT_ENTRY_RE.finditer(proj_section)):
                name = match.group(1).strip()
                text = match.group(2).strip()
                if text:
                    blocks.append({"index": i, "name": name, "text": text})

    return blocks[:10]


# ── Scoring ───────────────────────────────────────────────────────────────────

def _score_one_project(
    project_text: str,
    jd_text: str,
    jd_keywords: list[str],
    jd_skills: set[str],
) -> dict:
    if not project_text.strip():
        return {
            "technical_relevance": 0.0,
            "skill_overlap": 0.0,
            "keyword_overlap": 0.0,
            "semantic_similarity": 0.0,
            "matched_skills": [],
            "total": 0.0,
        }

    proj_lower = project_text.lower()

    # ── Skill overlap ──────────────────────────────────────────────────────
    proj_skills = set(extract_skills_from_text(project_text))
    matched_skills = sorted(proj_skills & jd_skills)
    skill_ratio = len(matched_skills) / max(len(jd_skills), 1)

    # ── Keyword overlap ────────────────────────────────────────────────────
    kw_hits = 0.0
    for kw in jd_keywords:
        if kw.lower() in proj_lower:
            kw_hits += 1.0
        else:
            words = proj_lower.split()
            if any(fuzz.ratio(kw.lower(), w) >= 85 for w in words):
                kw_hits += 0.5
    kw_ratio = kw_hits / max(len(jd_keywords), 1)

    # ── Semantic similarity ────────────────────────────────────────────────
    try:
        if len(project_text) >= 40 and len(jd_text) >= 40:
            sem = compute_semantic_similarity(project_text[:1200], jd_text[:1200]) / 100
        else:
            sem = (skill_ratio + kw_ratio) / 2
    except Exception:
        sem = (skill_ratio + kw_ratio) / 2

    total = min(100.0, (skill_ratio * 0.40 + kw_ratio * 0.35 + sem * 0.25) * 100)

    return {
        "technical_relevance": round(skill_ratio * 100, 1),
        "skill_overlap": round(skill_ratio * 100, 1),
        "keyword_overlap": round(kw_ratio * 100, 1),
        "semantic_similarity": round(sem * 100, 1),
        "matched_skills": matched_skills,
        "total": round(total, 1),
    }


def _recommend(score: float) -> dict:
    if score >= 75:
        return {"action": "MOVE UP", "detail": "High relevance — feature this project prominently.", "priority": "HIGH"}
    if score >= 50:
        return {"action": "EXPAND", "detail": "Good relevance — add more detail about the tech stack and outcomes.", "priority": "MEDIUM"}
    if score >= 25:
        return {"action": "MOVE DOWN", "detail": "Moderate relevance — keep but deprioritise for this application.", "priority": "LOW"}
    return {"action": "COMPRESS", "detail": "Low relevance — summarise briefly or omit for this application.", "priority": "NONE"}


def _portfolio_summary(projects: list[dict], avg: float) -> str:
    high = [p for p in projects if p["score"] >= 75]
    low = [p for p in projects if p["score"] < 25]
    parts: list[str] = []
    if high:
        names = ", ".join(p["name"] for p in high[:2])
        parts.append(f"Lead with {names} — highest relevance for this role")
    if low:
        names = ", ".join(p["name"] for p in low[:2])
        parts.append(f"Consider condensing '{names}' for this specific application")
    if avg < 30 and not high:
        parts.append("Consider adding projects that directly demonstrate the required tech stack")
    return ". ".join(parts) if parts else "Your project portfolio aligns well with this role"


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_project_relevance(resume_data: dict, jd_text: str) -> dict:
    """
    Score each project against the JD.

    Returns
    -------
    {
        has_projects: bool,
        projects: [{name, score, breakdown, recommendation, text_preview}],
        average_relevance: float,
        top_project: str | None,
        portfolio_summary: str,
    }
    """
    blocks = _extract_project_blocks(resume_data)

    if not blocks:
        return {
            "has_projects": False,
            "projects": [],
            "average_relevance": 0.0,
            "top_project": None,
            "portfolio_summary": (
                "No Projects section found. Adding 2-4 relevant projects is "
                "one of the highest-impact improvements for a fresher/student resume."
            ),
        }

    jd_keywords = extract_jd_keywords(jd_text)
    jd_skills = set(extract_skills_from_text(jd_text))

    scored: list[dict] = []
    for block in blocks:
        breakdown = _score_one_project(block["text"], jd_text, jd_keywords, jd_skills)
        scored.append({
            "name": block["name"],
            "index": block["index"],
            "score": breakdown["total"],
            "breakdown": breakdown,
            "recommendation": _recommend(breakdown["total"]),
            "text_preview": (
                block["text"][:200] + "…"
                if len(block["text"]) > 200
                else block["text"]
            ),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    avg = round(sum(p["score"] for p in scored) / len(scored), 1)

    return {
        "has_projects": True,
        "projects": scored,
        "average_relevance": avg,
        "top_project": scored[0]["name"] if scored else None,
        "portfolio_summary": _portfolio_summary(scored, avg),
    }
