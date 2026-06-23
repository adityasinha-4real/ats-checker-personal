"""Tests for ATS scoring engine."""
import pytest
from app.services.ats_scorer import (
    score_keywords, score_skills, score_experience,
    score_education, run_ats_analysis,
)


JD_TEXT = """
We are looking for a Senior Python Developer with 3+ years of experience.
Requirements:
- Strong Python programming skills
- Experience with FastAPI or Django
- Knowledge of React and TypeScript
- Database experience: PostgreSQL or MySQL
- Docker and Kubernetes experience
- Bachelor's degree in Computer Science or related field
- Experience with CI/CD pipelines
- Knowledge of machine learning is a plus
"""

RESUME_DATA_STRONG = {
    "raw_text": """
    John Doe - Senior Software Engineer
    john.doe@email.com | 555-0100

    EXPERIENCE
    Senior Python Developer at TechCorp 2021 - Present
    - Built FastAPI microservices serving 1M+ requests/day
    - Led migration from monolith to microservices architecture
    - Improved system performance by 40%

    Software Engineer at StartupXYZ 2019 - 2021
    - Developed React applications with TypeScript
    - Worked with PostgreSQL and Redis databases

    SKILLS
    Python, FastAPI, Django, React, TypeScript, JavaScript, PostgreSQL, MySQL,
    Docker, Kubernetes, CI/CD, GitHub Actions, Machine Learning, TensorFlow

    EDUCATION
    Bachelor of Science in Computer Science - MIT - 2019
    """,
    "skills": ["python", "fastapi", "django", "react", "typescript", "postgresql", "docker", "kubernetes"],
    "education_level": 3,
    "years_of_experience": 5,
    "word_count": 150,
    "sections_detected": ["experience", "skills", "education", "summary"],
}

RESUME_DATA_WEAK = {
    "raw_text": """
    Jane Smith
    jane@email.com

    EXPERIENCE
    Junior PHP Developer 2023 - Present

    SKILLS
    PHP, HTML, CSS, MySQL

    EDUCATION
    High School Diploma 2022
    """,
    "skills": ["php", "html", "css", "mysql"],
    "education_level": 0,
    "years_of_experience": 1,
    "word_count": 50,
    "sections_detected": ["experience", "skills", "education"],
}


def test_score_keywords_perfect_match():
    keywords = ["python", "fastapi", "docker"]
    text = "I have experience with Python, FastAPI, and Docker."
    score, matched, missing = score_keywords(text, keywords)
    assert score > 80
    assert len(matched) > 0
    assert len(missing) < len(keywords)


def test_score_keywords_no_match():
    keywords = ["java", "spring boot", "hibernate"]
    text = "Experienced in Python, Django, and PostgreSQL."
    score, matched, missing = score_keywords(text, keywords)
    assert score < 50
    assert len(missing) > 0


def test_score_keywords_empty_keywords():
    score, matched, missing = score_keywords("some text", [])
    assert score == 50.0
    assert matched == []
    assert missing == []


def test_score_skills_perfect():
    resume_skills = ["python", "fastapi", "docker", "react"]
    jd_skills = ["python", "fastapi", "docker"]
    score, matched, missing = score_skills(resume_skills, jd_skills)
    assert score == 100.0
    assert len(matched) == 3
    assert len(missing) == 0


def test_score_skills_partial():
    resume_skills = ["python", "django"]
    jd_skills = ["python", "fastapi", "react", "typescript"]
    score, matched, missing = score_skills(resume_skills, jd_skills)
    assert 0 < score < 100
    assert "python" in matched
    assert len(missing) > 0


def test_score_experience_exact():
    score = score_experience(3, "We require 3 years of experience")
    assert score == 100.0


def test_score_experience_exceeds():
    score = score_experience(5, "Minimum 3 years experience required")
    assert score == 100.0


def test_score_experience_less():
    score = score_experience(1, "5 years of experience required")
    assert score < 60


def test_score_experience_no_requirement():
    score = score_experience(2, "We are looking for a motivated developer")
    assert score == 70.0


def test_score_education_bachelor_match():
    score = score_education(3, "Bachelor's degree in Computer Science required")
    assert score == 100.0


def test_score_education_below_requirement():
    score = score_education(0, "Master's degree required")
    assert score < 70


def test_score_education_no_requirement():
    score = score_education(3, "Strong programming skills required")
    assert score == 80.0


def test_full_analysis_strong_resume():
    result = run_ats_analysis(RESUME_DATA_STRONG, JD_TEXT)
    assert result["overall_score"] > 50
    assert "keyword_score" in result
    assert "skills_score" in result
    assert "suggestions" in result
    assert isinstance(result["missing_skills"], list)
    assert isinstance(result["matched_skills"], list)


def test_full_analysis_weak_resume():
    result = run_ats_analysis(RESUME_DATA_WEAK, JD_TEXT)
    strong_result = run_ats_analysis(RESUME_DATA_STRONG, JD_TEXT)
    assert result["overall_score"] < strong_result["overall_score"]


def test_analysis_score_bounds():
    result = run_ats_analysis(RESUME_DATA_STRONG, JD_TEXT)
    for key in ["overall_score", "keyword_score", "skills_score", "experience_score", "education_score"]:
        assert 0 <= result[key] <= 100, f"{key} out of bounds: {result[key]}"


def test_analysis_suggestions_generated():
    result = run_ats_analysis(RESUME_DATA_WEAK, JD_TEXT)
    assert len(result["suggestions"]) > 0


def test_analysis_returns_required_fields():
    result = run_ats_analysis(RESUME_DATA_STRONG, JD_TEXT)
    required_fields = [
        "overall_score", "keyword_score", "skills_score",
        "experience_score", "education_score", "semantic_score",
        "missing_keywords", "missing_skills", "matched_keywords",
        "matched_skills", "suggestions", "details",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"
