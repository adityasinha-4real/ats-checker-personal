"""
Resume Optimizer — Feature 1.

Generates a tailored resume draft by:
1. Reordering sections based on JD relevance.
2. Prioritizing most relevant projects.
3. Reordering skills by JD importance.
4. Improving wording using existing resume content only.

Never invents experience, skills, or achievements.
All changes are marked SAFE or REQUIRES_VERIFICATION.
"""
from __future__ import annotations

from loguru import logger
from app.services.nlp_engine import extract_skills_from_text, normalize_skill


_WEAK_VERBS = {"worked", "helped", "assisted", "did", "made", "got", "used", "utilized", "was", "were"}
_STRONG_VERB_MAP = {
    "worked": "developed",
    "helped": "contributed to",
    "assisted": "supported",
    "did": "executed",
    "made": "built",
    "got": "achieved",
    "used": "leveraged",
    "utilized": "leveraged",
    "was": "served as",
    "were": "served as",
}


def _compute_section_order(resume_data: dict, jd_intelligence: dict, gap_analysis: dict) -> list[str]:
    """Determine optimal section order based on JD requirements."""
    years_exp = resume_data.get("years_of_experience", 0) or 0
    is_entry_level = (
        years_exp < 2
        or jd_intelligence.get("qualifications", {}).get("experience", {}).get("is_entry_level", False)
    )

    sections_present: set[str] = set()
    if resume_data.get("skills"):
        sections_present.add("skills")
    if resume_data.get("projects"):
        sections_present.add("projects")
    if resume_data.get("education"):
        sections_present.add("education")
    if resume_data.get("experience_entries"):
        sections_present.add("experience")
    if resume_data.get("certifications"):
        sections_present.add("certifications")
    for s in resume_data.get("sections_detected", []):
        sections_present.add(s)

    critical_missing = gap_analysis.get("critical_missing", [])

    if is_entry_level:
        preferred = ["skills", "projects", "education", "experience", "certifications"]
    elif len(critical_missing) > 3:
        preferred = ["skills", "experience", "projects", "education", "certifications"]
    else:
        preferred = ["experience", "skills", "projects", "education", "certifications"]

    return [s for s in preferred if s in sections_present]


def _reorder_skills(skills: list[str], jd_intelligence: dict, jd_text: str) -> dict:
    """Reorder skills with JD-matching skills first."""
    jd_skills_all: set[str] = set()
    for tech_list in jd_intelligence.get("technologies", {}).values():
        for t in tech_list:
            jd_skills_all.add(t.lower())
    for req in jd_intelligence.get("critical_requirements", []):
        jd_skills_all.update(req.lower().split())
    jd_skills_all.update(s.lower() for s in extract_skills_from_text(jd_text))

    primary: list[str] = []
    secondary: list[str] = []
    for skill in skills:
        skill_norm = normalize_skill(skill.lower())
        if (
            skill_norm in jd_skills_all
            or skill.lower() in jd_skills_all
            or any(skill.lower() in jd_s or jd_s in skill.lower() for jd_s in jd_skills_all)
        ):
            primary.append(skill)
        else:
            secondary.append(skill)

    return {"primary": primary, "secondary": secondary, "all": primary + secondary}


def _reorder_projects(projects: list[str], project_relevance: dict) -> list[str]:
    """Reorder projects by relevance score (highest first)."""
    if not project_relevance or not project_relevance.get("projects"):
        return projects
    scored = {p["index"]: p["score"] for p in project_relevance.get("projects", []) if "index" in p}
    indexed = sorted(enumerate(projects), key=lambda x: scored.get(x[0], 0), reverse=True)
    return [p for _, p in indexed]


def _improve_bullet(bullet: str, rewrites: dict, section: str) -> tuple[str, str]:
    """Return (improved_bullet, safety_flag). Falls back to weak-verb swap."""
    key_map = {"projects": "project_bullets", "experience": "experience_bullets"}
    suggestions = rewrites.get(key_map.get(section, ""), []) if rewrites else []

    for sug in suggestions:
        current = (sug.get("current") or "").lower()
        if current and (current[:40] in bullet.lower() or bullet.lower()[:40] in current):
            suggested = sug.get("suggested", "")
            if suggested and suggested != bullet:
                return suggested, sug.get("safety", "SAFE")

    words = bullet.split()
    if words and words[0].lower() in _WEAK_VERBS:
        strong = _STRONG_VERB_MAP.get(words[0].lower(), words[0])
        return strong.capitalize() + " " + " ".join(words[1:]), "SAFE"

    return bullet, "SAFE"


def generate_optimized_resume(
    resume_data: dict,
    jd_text: str,
    jd_intelligence: dict,
    gap_analysis: dict,
    project_relevance: dict,
    rewrites: dict,
) -> dict:
    """
    Generate a tailored resume draft.
    Only reorders, reprioritizes, and rewrites using existing content.
    """
    try:
        section_order = _compute_section_order(resume_data, jd_intelligence, gap_analysis)
        skills_data = _reorder_skills(resume_data.get("skills", []), jd_intelligence, jd_text)

        original_projects = resume_data.get("projects", [])
        reordered_projects = _reorder_projects(original_projects, project_relevance)

        project_entries: list[dict] = []
        for p in reordered_projects:
            opt, safety = _improve_bullet(p, rewrites, "projects")
            project_entries.append({"original": p, "optimized": opt, "safety": safety})

        experience_entries: list[dict] = []
        for entry in resume_data.get("experience_entries", []):
            snippet = entry.get("snippet", "")
            if snippet:
                opt, safety = _improve_bullet(snippet, rewrites, "experience")
                experience_entries.append({
                    "original": snippet,
                    "optimized": opt,
                    "safety": safety,
                    "start": entry.get("start", ""),
                    "end": entry.get("end", ""),
                })

        changes: list[dict] = []

        original_order = resume_data.get("sections_detected", [])
        if section_order and original_order and section_order != original_order:
            changes.append({
                "type": "REORDERED",
                "section": "sections",
                "description": f"Section order optimised to: {', '.join(section_order)}",
                "original": original_order,
                "optimized": section_order,
            })

        if skills_data["primary"] and skills_data["secondary"]:
            changes.append({
                "type": "REORDERED",
                "section": "skills",
                "description": f"{len(skills_data['primary'])} JD-matching skills moved to front",
                "original": (resume_data.get("skills") or [])[:5],
                "optimized": skills_data["all"][:5],
            })

        if original_projects and original_projects != reordered_projects:
            changes.append({
                "type": "REORDERED",
                "section": "projects",
                "description": "Projects reordered by JD relevance score",
                "original": original_projects[0][:80] if original_projects else "",
                "optimized": reordered_projects[0][:80] if reordered_projects else "",
            })

        rewritten_count = 0
        for entry in project_entries:
            if entry["original"] != entry["optimized"]:
                rewritten_count += 1
                changes.append({
                    "type": "REWRITTEN",
                    "section": "projects",
                    "description": "Project description improved",
                    "original": entry["original"][:120],
                    "optimized": entry["optimized"][:120],
                    "safety": entry["safety"],
                })
        for entry in experience_entries:
            if entry["original"] != entry["optimized"]:
                rewritten_count += 1
                changes.append({
                    "type": "REWRITTEN",
                    "section": "experience",
                    "description": "Experience bullet improved",
                    "original": entry["original"][:120],
                    "optimized": entry["optimized"][:120],
                    "safety": entry["safety"],
                })

        return {
            "name": resume_data.get("name"),
            "contact": {
                "email": resume_data.get("email"),
                "phone": resume_data.get("phone"),
                "linkedin": resume_data.get("linkedin"),
                "github": resume_data.get("github"),
            },
            "section_order": section_order,
            "skills": skills_data,
            "projects": project_entries,
            "experience": experience_entries,
            "education": resume_data.get("education", []),
            "certifications": resume_data.get("certifications", []),
            "changes": changes,
            "changes_summary": {
                "total_changes": len(changes),
                "sections_reordered": any(
                    c["type"] == "REORDERED" and c["section"] == "sections" for c in changes
                ),
                "skills_reordered": any(
                    c["type"] == "REORDERED" and c["section"] == "skills" for c in changes
                ),
                "projects_reordered": any(
                    c["type"] == "REORDERED" and c["section"] == "projects" for c in changes
                ),
                "bullets_rewritten": rewritten_count,
            },
        }
    except Exception as e:
        logger.error(f"Resume optimization failed: {e}")
        return {
            "name": resume_data.get("name"),
            "contact": {},
            "section_order": [],
            "skills": {"primary": [], "secondary": [], "all": resume_data.get("skills", [])},
            "projects": [],
            "experience": [],
            "education": resume_data.get("education", []),
            "certifications": resume_data.get("certifications", []),
            "changes": [],
            "changes_summary": {
                "total_changes": 0,
                "sections_reordered": False,
                "skills_reordered": False,
                "projects_reordered": False,
                "bullets_rewritten": 0,
            },
        }
