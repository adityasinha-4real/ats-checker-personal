"""
Skill Gap Roadmap — Feature 4.
Takes Market Analyzer missing_from_profile output and ranks learning priorities
into timed phases. No external data sources — purely derived from market analysis.
"""
from __future__ import annotations

from typing import Any


_CATEGORY_PRIORITY = {
    "programming_languages": 1.5,
    "frameworks": 1.3,
    "cloud": 1.2,
    "databases": 1.1,
    "tools": 1.0,
    "concepts": 0.9,
}

_CATEGORY_LABELS = {
    "programming_languages": "Programming Language",
    "frameworks": "Framework / Library",
    "cloud": "Cloud / DevOps",
    "databases": "Database",
    "tools": "Tool / Platform",
    "concepts": "Concept / Methodology",
}

_WHY_TEMPLATES = {
    "programming_languages": "High-demand language appearing in {pct}% of market JDs. Core to many modern stacks.",
    "frameworks": "Framework requested in {pct}% of JDs. Directly accelerates project delivery.",
    "cloud": "Cloud skill in {pct}% of JDs. Required for deployment and infrastructure roles.",
    "databases": "Database skill found in {pct}% of JDs. Essential for back-end development.",
    "tools": "Tool present in {pct}% of JDs. Improves development velocity and DevOps fit.",
    "concepts": "Concept present in {pct}% of JDs. Broadens architectural thinking.",
}


def _priority_score(entry: dict[str, Any]) -> float:
    pct = entry.get("percentage", 0)
    cat = entry.get("category", "tools")
    mult = _CATEGORY_PRIORITY.get(cat, 1.0)
    return round(pct * mult, 2)


def generate_roadmap(
    missing_skills: list[dict[str, Any]],
    market_analysis: dict[str, Any] | None = None,
    resume_skills: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a phased learning roadmap from missing skill entries.

    Each entry in missing_skills is expected to have:
      { skill, count, percentage, category }
    """
    if not missing_skills:
        return {
            "phases": [],
            "total_skills": 0,
            "total_phases": 0,
            "learning_focus": "No skill gaps detected — profile already covers the market.",
        }

    # Score and sort all missing skills
    scored: list[dict[str, Any]] = []
    for entry in missing_skills:
        skill = entry.get("skill", "")
        category = entry.get("category", "tools")
        pct = entry.get("percentage", 0)
        count = entry.get("count", 0)
        score = _priority_score(entry)
        why_tmpl = _WHY_TEMPLATES.get(category, "Appears in {pct}% of market JDs.")
        scored.append({
            "skill": skill,
            "category": _CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
            "market_demand": pct,
            "priority_score": score,
            "why": why_tmpl.format(pct=pct, count=count),
        })

    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    # Split into phases: immediate top-5, medium next-7, long rest
    phase1_skills = scored[:5]
    phase2_skills = scored[5:12]
    phase3_skills = scored[12:]

    phases = []
    if phase1_skills:
        phases.append({
            "phase": 1,
            "label": "Immediate Priority",
            "timeframe": "0–3 months",
            "skills": phase1_skills,
        })
    if phase2_skills:
        phases.append({
            "phase": 2,
            "label": "Medium-Term",
            "timeframe": "3–6 months",
            "skills": phase2_skills,
        })
    if phase3_skills:
        phases.append({
            "phase": 3,
            "label": "Long-Term",
            "timeframe": "6–12 months",
            "skills": phase3_skills,
        })

    # Derive overall learning focus from top category
    top_categories: dict[str, int] = {}
    for s in scored[:5]:
        cat = s["category"]
        top_categories[cat] = top_categories.get(cat, 0) + 1
    dominant = max(top_categories, key=top_categories.get) if top_categories else "mixed"

    focus_map = {
        "Programming Language": "core language expansion",
        "Framework / Library": "framework depth",
        "Cloud / DevOps": "cloud and infrastructure",
        "Database": "data layer skills",
        "Tool / Platform": "tooling and DevOps",
        "Concept / Methodology": "software engineering practices",
    }
    learning_focus = f"Focus on {focus_map.get(dominant, dominant)} to maximise market fit."

    return {
        "phases": phases,
        "total_skills": len(scored),
        "total_phases": len(phases),
        "learning_focus": learning_focus,
    }
