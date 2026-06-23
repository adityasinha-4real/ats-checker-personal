"""
Competitiveness Analysis — Feature 5.
Classifies the application as: Strong Match / Reasonable Match / Stretch Application / Low Probability.
"""
from __future__ import annotations

_LABEL_MAP = {
    "STRONG_MATCH": "Strong Match",
    "REASONABLE_MATCH": "Reasonable Match",
    "STRETCH": "Stretch Application",
    "LOW_PROBABILITY": "Low Probability",
}


def analyze_competitiveness(
    ats_result: dict,
    gap_analysis: dict,
    project_relevance: dict | None = None,
) -> dict:
    """
    Composite score: ATS overall (50%) + gap coverage (30%) + project relevance (20%).
    """
    overall = float(ats_result.get("overall_score", 50))
    severity = float(gap_analysis.get("severity_score", 50))
    critical_count = int(gap_analysis.get("critical_count", 0))
    avg_proj = float((project_relevance or {}).get("average_relevance", 50))

    gap_coverage = max(0.0, 100.0 - severity)
    composite = round(overall * 0.50 + gap_coverage * 0.30 + avg_proj * 0.20, 1)

    if composite >= 70 and critical_count <= 1:
        key = "STRONG_MATCH"
        explanation = (
            f"Your profile aligns well with this role (composite: {composite}/100). "
            f"ATS score {overall:.0f}/100 with only {critical_count} critical gap(s). "
            "High interview likelihood."
        )
    elif composite >= 50 and critical_count <= 3:
        key = "REASONABLE_MATCH"
        explanation = (
            f"Solid match with some gaps (composite: {composite}/100). "
            f"ATS score {overall:.0f}/100, {critical_count} critical gap(s). "
            "Addressing missing skills will improve chances."
        )
    elif composite >= 35:
        key = "STRETCH"
        explanation = (
            f"Challenging but possible (composite: {composite}/100). "
            f"ATS score {overall:.0f}/100, {critical_count} critical gap(s). "
            "Significant preparation needed."
        )
    else:
        key = "LOW_PROBABILITY"
        explanation = (
            f"Significant skill/experience mismatch (composite: {composite}/100). "
            f"ATS score {overall:.0f}/100, {critical_count} critical gap(s). "
            "Consider building relevant experience first."
        )

    return {
        "label": _LABEL_MAP[key],
        "label_key": key,
        "composite_score": composite,
        "explanation": explanation,
        "detailed_factors": {
            "ats_score": overall,
            "gap_severity": severity,
            "critical_gaps": critical_count,
            "project_relevance": avg_proj,
            "gap_coverage": round(gap_coverage, 1),
        },
    }
