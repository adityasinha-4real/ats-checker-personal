"""
Interview Probability — Feature 4.
Computes 0-100 interview probability from all analysis signals.
"""
from __future__ import annotations


def compute_interview_probability(
    ats_result: dict,
    gap_analysis: dict,
    project_relevance: dict | None,
    quality_audit: dict,
) -> dict:
    """
    Weighted probability across six factors.

    Weights:
      gap_coverage      25%  (inverse of critical gap severity)
      skills_match      20%
      project_relevance 20%
      resume_quality    15%
      education_fit     10%
      semantic_match    10%
    """
    severity = gap_analysis.get("severity_score", 50)
    gap_factor = max(0.0, 100.0 - severity)

    skills_score = float(ats_result.get("skills_score", 50))
    avg_proj = float((project_relevance or {}).get("average_relevance", 50))
    quality_score = float(quality_audit.get("quality_score", 70))
    education_score = float(ats_result.get("education_score", 50))
    semantic_score = float(ats_result.get("semantic_score", 50))

    probability = (
        gap_factor * 0.25
        + skills_score * 0.20
        + avg_proj * 0.20
        + quality_score * 0.15
        + education_score * 0.10
        + semantic_score * 0.10
    )
    probability = max(0.0, min(100.0, round(probability, 1)))

    if probability >= 70:
        label = "HIGH"
    elif probability >= 50:
        label = "MEDIUM"
    elif probability >= 30:
        label = "LOW"
    else:
        label = "VERY LOW"

    factors = [
        {"name": "Gap Coverage", "score": round(gap_factor, 1), "weight": "25%",
         "description": "Inverse of critical skill gap severity"},
        {"name": "Skills Match", "score": round(skills_score, 1), "weight": "20%",
         "description": "Skills overlap with the job description"},
        {"name": "Project Relevance", "score": round(avg_proj, 1), "weight": "20%",
         "description": "How relevant your projects are to the role"},
        {"name": "Resume Quality", "score": round(quality_score, 1), "weight": "15%",
         "description": "Overall resume completeness and quality"},
        {"name": "Education Fit", "score": round(education_score, 1), "weight": "10%",
         "description": "Education level relative to requirements"},
        {"name": "Semantic Match", "score": round(semantic_score, 1), "weight": "10%",
         "description": "Overall content similarity to the JD"},
    ]

    bottleneck = min(factors, key=lambda f: f["score"])
    strength = max(factors, key=lambda f: f["score"])

    if probability >= 70:
        reasoning = (
            f"Strong overall profile. Top strength: {strength['name']} ({strength['score']:.0f}/100). "
            "High likelihood of reaching interview stage."
        )
    elif probability >= 50:
        reasoning = (
            f"Competitive profile with room to improve. Main weakness: "
            f"{bottleneck['name']} ({bottleneck['score']:.0f}/100). "
            "Addressing gaps will meaningfully improve chances."
        )
    elif probability >= 30:
        reasoning = (
            f"Significant gaps detected in {bottleneck['name']} ({bottleneck['score']:.0f}/100). "
            "Targeted preparation is needed before applying."
        )
    else:
        reasoning = (
            f"Critical mismatch in {bottleneck['name']} ({bottleneck['score']:.0f}/100). "
            "Consider building more relevant skills and projects before applying."
        )

    return {
        "probability": probability,
        "label": label,
        "factors": factors,
        "reasoning": reasoning,
        "top_strength": strength["name"],
        "main_bottleneck": bottleneck["name"],
    }
