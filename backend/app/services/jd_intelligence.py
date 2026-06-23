"""
JD Intelligence Engine — Phase 1.
Classifies job description text into structured requirement categories.
"""
from __future__ import annotations

import re
from loguru import logger
from app.services.nlp_engine import extract_skills_from_text, TECH_SKILLS, SKILL_ALIASES

# ── Requirement signal patterns ───────────────────────────────────────────────

REQUIRED_SIGNALS = [
    r"\brequired\b", r"\bmust[\s-]have\b", r"\bmandatory\b",
    r"\bminimum\s+qualifications?\b", r"\bminimum\s+requirements?\b",
    r"\bessential\b", r"\byou\s+must\b", r"\byou\s+will\s+need\b",
    r"\bwill\s+be\s+expected\s+to\b", r"\bmust\s+be\s+able\s+to\b",
    r"\bbasic\s+qualifications?\b",
]

PREFERRED_SIGNALS = [
    r"\bpreferred\b", r"\bgood[\s-]to[\s-]have\b", r"\bbonus\b",
    r"\bnice[\s-]to[\s-]have\b", r"\badvantage\b", r"\bdesirable\b",
    r"\bideal\b", r"\bwould\s+be\s+(?:a\s+)?plus\b", r"\boptional\b",
    r"\bif\s+you\s+have\b", r"\bwelcome\b", r"\bwould\s+be\s+great\b",
    r"\badditional\s+qualifications?\b",
]

SOFT_SKILLS_VOCAB = [
    "communication", "teamwork", "leadership", "problem.solving",
    "critical thinking", "adaptability", "time management", "collaboration",
    "interpersonal", "analytical", "detail.oriented", "self.motivated",
    "organized", "multitasking", "creativity", "initiative",
    "work independently", "team player", "fast learner", "proactive",
    "result.oriented", "customer.focused", "self-starter",
    "conflict resolution", "decision making", "emotional intelligence",
    "presentation skills", "written communication", "verbal communication",
]

CERT_KEYWORDS = [
    "aws certified", "azure certified", "google cloud certified",
    "cka", "ckad", "pmp", "ccna", "ccnp", "cissp", "cism", "cisa",
    "security+", "comptia", "gcp professional", "azure administrator",
    "solutions architect", "developer associate", "sysops",
    "hashicorp certified", "terraform associate",
]


# ── Section splitter ─────────────────────────────────────────────────────────

_REQ_HEADERS = [
    r"required\s+qualifications?", r"minimum\s+qualifications?",
    r"what\s+you.ll\s+need", r"what\s+you\s+need", r"must\s+have",
    r"basic\s+qualifications?", r"requirements?(\s*:)?$",
    r"you\s+will\s+(?:need|have)", r"key\s+requirements?",
]
_PREF_HEADERS = [
    r"preferred\s+qualifications?", r"nice[\s-]to[\s-]have",
    r"bonus\s+(?:qualifications?|points?|skills?)?",
    r"good[\s-]to[\s-]have", r"additional\s+qualifications?",
    r"plus\s+if\s+you\s+have", r"desired\s+(?:qualifications?|skills?)",
]


def _split_jd_sections(text: str) -> tuple[str, str]:
    """Return (required_section_text, preferred_section_text)."""
    lines = text.splitlines()
    req_lines: list[str] = []
    pref_lines: list[str] = []
    current = "general"

    for line in lines:
        ll = line.lower().strip()
        if not ll:
            continue
        if len(ll) < 80:
            if any(re.search(p, ll) for p in _REQ_HEADERS):
                current = "required"
                continue
            if any(re.search(p, ll) for p in _PREF_HEADERS):
                current = "preferred"
                continue
        if current == "required":
            req_lines.append(line)
        elif current == "preferred":
            pref_lines.append(line)

    return "\n".join(req_lines), "\n".join(pref_lines)


# ── Sentence-level classification ────────────────────────────────────────────

def _classify_sentence(sentence: str) -> str:
    sl = sentence.lower()
    for p in REQUIRED_SIGNALS:
        if re.search(p, sl):
            return "required"
    for p in PREFERRED_SIGNALS:
        if re.search(p, sl):
            return "preferred"
    return "general"


# ── Sub-extractors ───────────────────────────────────────────────────────────

def _extract_experience_req(text: str) -> dict:
    patterns = [
        (r"(\d+)\+?\s*[-–]\s*(\d+)\s*years?", True),
        (r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:work\s+)?(?:relevant\s+)?experience", False),
        (r"minimum\s+(?:of\s+)?(\d+)\s*years?", False),
        (r"at\s+least\s+(\d+)\s*years?", False),
        (r"(\d+)\+\s*years?", False),
    ]
    for pattern, is_range in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                lo = int(m.group(1))
                hi = int(m.group(2)) if is_range and m.lastindex >= 2 else lo
                return {
                    "min_years": lo,
                    "max_years": hi,
                    "description": m.group(0).strip(),
                    "is_entry_level": lo == 0,
                }
            except (ValueError, IndexError):
                pass

    entry_patterns = [
        r"entry[\s-]level", r"\bfresher\b", r"new\s+graduate",
        r"recent\s+graduate", r"\bintern\b", r"0\s*[-–]\s*\d+\s*years?",
    ]
    for p in entry_patterns:
        if re.search(p, text, re.IGNORECASE):
            return {"min_years": 0, "max_years": 2, "description": "Entry level / Fresher", "is_entry_level": True}

    return {"min_years": None, "max_years": None, "description": "Not specified", "is_entry_level": False}


_EDU_LEVELS = {
    "phd": (["phd", "ph.d", "doctorate", "doctoral"], 5),
    "masters": (["master's", "masters", "msc", "ms degree", "mba", "m.s.", "m.e.", "m.tech"], 4),
    "bachelors": (["bachelor's", "bachelors", "bsc", "bs degree", "be degree", "b.tech", "b.e.", "undergraduate degree", "bachelor of"], 3),
    "associate": (["associate's", "associate degree"], 2),
}


def _extract_education_req(text: str) -> dict:
    tl = text.lower()
    found = []
    for level, (phrases, rank) in _EDU_LEVELS.items():
        for ph in phrases:
            if ph in tl:
                found.append((rank, level))
                break
    if not found:
        # Check for "equivalent experience" shorthand
        if "equivalent experience" in tl or "or equivalent" in tl:
            return {"level": "flexible", "description": "Degree or equivalent experience"}
        return {"level": "not_specified", "description": "Not specified"}
    found.sort(reverse=True)
    rank, level = found[0]
    return {"level": level, "description": f"{level.capitalize()} degree required"}


def _extract_soft_skills(text: str) -> list[str]:
    tl = text.lower()
    found = []
    for skill in SOFT_SKILLS_VOCAB:
        pattern = skill.replace(".", r"[\s\-]?")
        if re.search(r"\b" + pattern + r"\b", tl):
            found.append(skill.replace(".", " "))
    return found


def _extract_certifications(text: str) -> list[str]:
    tl = text.lower()
    found = []
    for cert in CERT_KEYWORDS:
        if cert in tl:
            found.append(cert.title())
    pattern = r"(?:certified|certification)\s+in\s+([\w\s]+?)(?:\.|,|\n|$)"
    for m in re.finditer(pattern, text, re.IGNORECASE):
        c = m.group(1).strip()
        if c and len(c) < 60 and c.lower() not in found:
            found.append(c.title())
    return list(dict.fromkeys(found))


def _categorise_skills(skills: list[str]) -> dict[str, list[str]]:
    """Bucket a flat skills list into tech categories."""
    bucket: dict[str, list[str]] = {k: [] for k in TECH_SKILLS}
    for cat, members in TECH_SKILLS.items():
        for m in members:
            if m in skills and m not in bucket[cat]:
                bucket[cat].append(m)
    # flatten frontend/backend → frameworks
    result = {
        "languages": bucket["languages"],
        "frameworks": sorted(set(bucket["frontend"] + bucket["backend"] + bucket["mobile"])),
        "databases": bucket["databases"],
        "cloud": bucket["cloud"],
        "devops": bucket["devops"],
        "ml_ai": bucket["ml_ai"],
        "tools": sorted(set(bucket["tools"] + bucket["data_engineering"] + bucket["security"])),
    }
    return {k: v for k, v in result.items() if v}


# ── Main entry point ─────────────────────────────────────────────────────────

def classify_jd(jd_text: str) -> dict:
    """
    Classify a job description into structured intelligence.

    Returns
    -------
    {
        critical_requirements: list[str],
        preferred_requirements: list[str],
        technologies: {languages, frameworks, databases, cloud, devops, tools, ml_ai},
        qualifications: {experience, education, certifications},
        soft_skills: list[str],
    }
    """
    req_section, pref_section = _split_jd_sections(jd_text)

    all_skills = extract_skills_from_text(jd_text)
    req_skills = set(extract_skills_from_text(req_section)) if req_section else set()
    pref_skills = set(extract_skills_from_text(pref_section)) if pref_section else set()

    # Sentence-level pass for skills not in explicit sections
    critical: set[str] = set(req_skills)
    preferred: set[str] = set(pref_skills)

    sentences = re.split(r"[.\n•\-\*]+", jd_text)
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 8:
            continue
        cls = _classify_sentence(sent)
        sent_skills = set(extract_skills_from_text(sent))
        if cls == "required":
            critical.update(sent_skills)
        elif cls == "preferred":
            preferred.update(sent_skills - critical)

    # Remaining unclassified skills: check proximity to required language
    classified = critical | preferred
    unclassified = [s for s in all_skills if s not in classified]
    for skill in unclassified:
        window = r"(?:" + "|".join(REQUIRED_SIGNALS) + r").{0,120}" + re.escape(skill)
        if re.search(window, jd_text.lower()):
            critical.add(skill)
        else:
            preferred.add(skill)

    # Fallback: if nothing classified, split all_skills 60/40
    if not critical and all_skills:
        split = max(1, len(all_skills) * 6 // 10)
        critical = set(all_skills[:split])
        preferred = set(all_skills[split:])

    # Remove skills from preferred that ended up in critical
    preferred -= critical

    technologies = _categorise_skills(all_skills)
    experience_req = _extract_experience_req(jd_text)
    education_req = _extract_education_req(jd_text)
    certifications = _extract_certifications(jd_text)
    soft_skills = _extract_soft_skills(jd_text)

    logger.debug(f"JD classified: {len(critical)} critical, {len(preferred)} preferred skills")

    return {
        "critical_requirements": sorted(critical),
        "preferred_requirements": sorted(preferred),
        "technologies": technologies,
        "qualifications": {
            "experience": experience_req,
            "education": education_req,
            "certifications": certifications,
        },
        "soft_skills": soft_skills,
    }
