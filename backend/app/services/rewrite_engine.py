"""
Smart Resume Rewrite Engine — Phase 3.
Generates actionable bullet rewrites from existing resume content.
Never fabricates experience; only reworks what's already there.
"""
from __future__ import annotations

import re

STRONG_VERBS = [
    "Developed", "Built", "Implemented", "Designed", "Architected",
    "Optimized", "Improved", "Deployed", "Integrated", "Created",
    "Led", "Delivered", "Automated", "Analyzed", "Configured",
    "Migrated", "Refactored", "Scaled", "Launched", "Engineered",
    "Established", "Reduced", "Increased", "Mentored", "Executed",
    "Spearheaded", "Streamlined", "Accelerated", "Maintained",
]

WEAK_PREFIXES = [
    "worked on", "helped with", "assisted with", "was responsible for",
    "helped to", "assisted in", "participated in", "involved in",
    "contributed to", "responsible for",
]

# Maps a skill to a brief descriptive phrase used in generated suggestions
_SKILL_CONTEXT: dict[str, str] = {
    "docker": "containerizing the application for consistent deployment",
    "kubernetes": "orchestrating containerized services at scale",
    "aws": "deploying infrastructure on AWS cloud",
    "azure": "managing resources on Azure cloud",
    "gcp": "running workloads on Google Cloud Platform",
    "ci/cd": "automating build, test, and deployment pipelines",
    "postgresql": "managing relational data with PostgreSQL",
    "mongodb": "handling NoSQL data with MongoDB",
    "redis": "implementing caching and session management via Redis",
    "react": "building dynamic, component-driven user interfaces with React",
    "fastapi": "serving high-performance REST APIs with FastAPI",
    "django": "developing a full-stack web application using Django",
    "flask": "building lightweight microservices with Flask",
    "node.js": "serving real-time features via Node.js",
    "graphql": "exposing a flexible GraphQL API",
    "typescript": "ensuring type-safety across the codebase with TypeScript",
    "machine learning": "training and evaluating machine learning models",
    "tensorflow": "implementing neural network architectures with TensorFlow",
    "pytorch": "conducting deep learning experiments with PyTorch",
    "git": "managing version control and collaboration via Git",
    "sql": "querying and optimising relational database operations",
    "linux": "administering Linux/Unix server environments",
    "microservices": "decomposing monolithic services into microservices",
    "rest": "designing and consuming RESTful APIs",
    "kafka": "streaming data at scale with Apache Kafka",
    "spark": "processing large datasets with Apache Spark",
    "terraform": "provisioning infrastructure as code with Terraform",
    "ansible": "automating configuration management with Ansible",
}


def _default_context(skill: str) -> str:
    return f"{skill} for improved scalability and performance"


def _extract_bullets(text: str) -> list[str]:
    """Pull bullet-style lines and action-verb sentences from text."""
    bullets: list[str] = []
    seen: set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        # Strip common bullet markers
        clean = re.sub(r"^[•\-\*–▸▹○●►]\s*", "", line).strip()
        if len(clean) > 18 and clean not in seen:
            bullets.append(clean)
            seen.add(clean)

    # Also pull sentences that start with strong verbs
    for sent in re.split(r"(?<=[.!?])\s+", text):
        sent = sent.strip()
        if len(sent) > 20 and any(sent.lower().startswith(v.lower()) for v in STRONG_VERBS):
            if sent not in seen:
                bullets.append(sent)
                seen.add(sent)

    return bullets[:25]


def _try_rewrite(bullet: str, skill: str) -> tuple[str | None, str]:
    """
    Attempt to enhance *bullet* to surface *skill*.
    Returns (rewritten_text | None, safety_flag).
    safety_flag: 'SAFE' if based on existing content, 'REQUIRES_VERIFICATION' otherwise.
    """
    if skill.lower() in bullet.lower():
        return None, "SAFE"

    ctx = _SKILL_CONTEXT.get(skill.lower(), _default_context(skill))

    # Replace weak prefix
    for weak in WEAK_PREFIXES:
        if bullet.lower().startswith(weak):
            rest = bullet[len(weak):].strip().rstrip(".")
            return f"Developed {rest}, leveraging {skill} for {ctx}.", "SAFE"

    # Append skill to existing strong-verb bullet
    if any(bullet.lower().startswith(v.lower()) for v in STRONG_VERBS):
        base = bullet.rstrip(".")
        if " using " not in base.lower() and " with " not in base.lower():
            return f"{base} using {skill}.", "SAFE"
        return f"{base}, integrating {skill} for {ctx}.", "SAFE"

    # Noun phrase → wrap in action verb
    return f"Implemented {bullet.rstrip('.').lower()} using {skill} to enable {ctx}.", "SAFE"


# ── Public API ───────────────────────────────────────────────────────────────

def generate_skills_section_suggestions(
    resume_data: dict,
    gap_analysis: dict,
) -> list[dict]:
    suggestions: list[dict] = []
    resume_skills_lower = {s.lower() for s in resume_data.get("skills", [])}

    for skill in gap_analysis.get("critical_missing", [])[:6]:
        if skill.lower() not in resume_skills_lower:
            suggestions.append({
                "type": "skills_section",
                "impact": "HIGH",
                "skill": skill,
                "suggestion": (
                    f"Add '{skill}' to your Skills section. "
                    "Only add it if you have genuine exposure — even academic projects count."
                ),
                "safety": "REQUIRES_VERIFICATION",
            })

    for skill in gap_analysis.get("important_missing", [])[:4]:
        if skill.lower() not in resume_skills_lower:
            suggestions.append({
                "type": "skills_section",
                "impact": "MEDIUM",
                "skill": skill,
                "suggestion": (
                    f"Consider listing '{skill}' under Skills if you have any familiarity with it."
                ),
                "safety": "REQUIRES_VERIFICATION",
            })

    return suggestions


def generate_project_bullet_suggestions(
    resume_data: dict,
    gap_analysis: dict,
) -> list[dict]:
    suggestions: list[dict] = []
    raw_text = resume_data.get("raw_text", "") or ""
    bullets = _extract_bullets(raw_text)

    for skill in gap_analysis.get("critical_missing", [])[:6]:
        best: str | None = None
        safety = "REQUIRES_VERIFICATION"

        for bullet in bullets:
            rewritten, s = _try_rewrite(bullet, skill)
            if rewritten:
                best = rewritten
                safety = s
                original = bullet
                break

        if best:
            suggestions.append({
                "type": "project_bullet",
                "impact": "HIGH",
                "skill": skill,
                "current": original,
                "suggested": best,
                "safety": safety,
                "note": "Rework of existing content — verify accuracy before submitting.",
            })
        else:
            ctx = _SKILL_CONTEXT.get(skill.lower(), _default_context(skill))
            suggestions.append({
                "type": "project_bullet",
                "impact": "HIGH",
                "skill": skill,
                "current": None,
                "suggested": (
                    f"Built [Project Name] using {skill} to {ctx} — "
                    f"[describe outcome/metric]."
                ),
                "safety": "REQUIRES_VERIFICATION",
                "note": "Template — fill in your actual project details.",
            })

    return suggestions


def generate_experience_bullet_suggestions(
    resume_data: dict,
    gap_analysis: dict,
) -> list[dict]:
    suggestions: list[dict] = []
    raw_text = resume_data.get("raw_text", "") or ""
    bullets = _extract_bullets(raw_text)

    # Weak verb strengthening
    for bullet in bullets[:10]:
        for weak in WEAK_PREFIXES:
            if bullet.lower().startswith(weak):
                rest = bullet[len(weak):].strip().rstrip(".")
                suggestions.append({
                    "type": "experience_bullet",
                    "impact": "MEDIUM",
                    "current": bullet,
                    "suggested": f"Developed {rest}.",
                    "safety": "SAFE",
                    "note": "Replaced weak opening with strong action verb.",
                })
                break
        if len(suggestions) >= 3:
            break

    # Metrics nudge
    if not re.search(r"(\d+%|\$[\d,]+|\d+[xX]|\d+k\+?|\d+\s+(?:users?|requests?))", raw_text, re.IGNORECASE):
        suggestions.append({
            "type": "experience_bullet",
            "impact": "HIGH",
            "current": None,
            "suggested": (
                "Quantify your achievements: e.g., "
                "'Reduced API latency by 40%', 'Scaled service to 10K+ daily users', "
                "'Decreased build time from 12 min to 3 min'."
            ),
            "safety": "REQUIRES_VERIFICATION",
            "note": "Adding numbers significantly increases recruiter attention.",
        })

    return suggestions


def _priority_list(gap_analysis: dict) -> list[dict]:
    items: list[dict] = []
    for skill in gap_analysis.get("critical_missing", [])[:5]:
        items.append({
            "skill": skill,
            "priority": "HIGH IMPACT",
            "action": f"Add '{skill}' to Skills section and mention in project/experience bullets.",
        })
    for skill in gap_analysis.get("important_missing", [])[:4]:
        items.append({
            "skill": skill,
            "priority": "MEDIUM IMPACT",
            "action": f"Mention '{skill}' where genuinely applicable in your resume.",
        })
    for skill in gap_analysis.get("optional_missing", [])[:3]:
        items.append({
            "skill": skill,
            "priority": "LOW IMPACT",
            "action": f"Optionally include '{skill}' if you have any exposure.",
        })
    return items


def generate_all_rewrites(
    resume_data: dict,
    gap_analysis: dict,
) -> dict:
    return {
        "skills_section": generate_skills_section_suggestions(resume_data, gap_analysis),
        "project_bullets": generate_project_bullet_suggestions(resume_data, gap_analysis),
        "experience_bullets": generate_experience_bullet_suggestions(resume_data, gap_analysis),
        "priority_list": _priority_list(gap_analysis),
    }
