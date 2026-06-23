"""Tests for resume parser utilities."""
import pytest
from app.utils.helpers import (
    extract_emails, extract_phones, extract_sections,
    extract_years_of_experience, clean_text,
)
from app.services.nlp_engine import (
    extract_skills_from_text, extract_education_level,
    extract_keywords_tfidf,
)


def test_extract_emails():
    text = "Contact me at john.doe@example.com or support@company.org"
    emails = extract_emails(text)
    assert "john.doe@example.com" in emails
    assert "support@company.org" in emails


def test_extract_emails_empty():
    assert extract_emails("No email here") == []


def test_extract_phones():
    text = "Call me at 123-456-7890 or (555) 123-4567"
    phones = extract_phones(text)
    assert len(phones) >= 1


def test_clean_text():
    text = "Hello   World\n\nTest  \t\t text"
    cleaned = clean_text(text)
    assert "  " not in cleaned
    assert cleaned == cleaned.strip()


def test_extract_sections():
    text = """John Doe
john@example.com

EXPERIENCE
Software Engineer at Acme Corp 2020-2022

EDUCATION
B.S. Computer Science, MIT 2020

SKILLS
Python, JavaScript, React"""
    sections = extract_sections(text)
    assert "experience" in sections or "education" in sections or "skills" in sections


def test_extract_years_of_experience():
    text = "Software Engineer 2019 - Present. Previous role 2017 - 2019."
    years = extract_years_of_experience(text)
    assert years >= 0


def test_extract_years_text_pattern():
    text = "I have 5+ years of experience in software development."
    years = extract_years_of_experience(text)
    assert years >= 5


def test_extract_skills_python():
    text = "Experienced in Python, JavaScript, and React. Also know Docker and Kubernetes."
    skills = extract_skills_from_text(text)
    assert "python" in skills
    assert "javascript" in skills
    assert "react" in skills
    assert "docker" in skills


def test_extract_skills_empty():
    skills = extract_skills_from_text("")
    assert skills == []


def test_extract_education_level_bachelor():
    text = "Bachelor of Science in Computer Science from MIT"
    level = extract_education_level(text)
    assert level >= 3


def test_extract_education_level_master():
    text = "Master of Science in Machine Learning from Stanford"
    level = extract_education_level(text)
    assert level >= 4


def test_extract_education_level_none():
    text = "Some random text with no education info"
    level = extract_education_level(text)
    assert level == 0


def test_tfidf_keywords():
    text = "Python developer with experience in machine learning and deep learning. Worked with TensorFlow and PyTorch for 3 years."
    keywords = extract_keywords_tfidf(text, top_n=10)
    assert isinstance(keywords, list)
    assert len(keywords) > 0
