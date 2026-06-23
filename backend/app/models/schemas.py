from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ResumeBase(BaseModel):
    original_filename: str
    file_type: str


class ResumeResponse(ResumeBase):
    id: int
    filename: str
    file_path: str
    raw_text: str | None = None
    parsed_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeListItem(BaseModel):
    id: int
    original_filename: str
    file_type: str
    created_at: datetime
    parsed_data: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class JobDescriptionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    description: str = Field(..., min_length=10)


class JobDescriptionUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    description: str | None = None


class JobDescriptionResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    parsed_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobDescriptionListItem(BaseModel):
    id: int
    title: str
    company: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisRequest(BaseModel):
    resume_id: int
    jd_id: int | None = None
    jd_text: str | None = None
    jd_title: str = "Quick Analysis"
    jd_company: str = ""


class BulkAnalysisRequest(BaseModel):
    resume_ids: list[int]
    jd_id: int | None = None
    jd_text: str | None = None
    jd_title: str = "Bulk Analysis"
    jd_company: str = ""


class ScoreBreakdown(BaseModel):
    keyword_score: float
    skills_score: float
    experience_score: float
    education_score: float
    semantic_score: float
    overall_score: float


class AnalysisResponse(BaseModel):
    id: int
    resume_id: int
    jd_id: int
    overall_score: float
    keyword_score: float
    skills_score: float
    experience_score: float
    education_score: float
    semantic_score: float
    missing_keywords: list[str]
    missing_skills: list[str]
    matched_keywords: list[str]
    matched_skills: list[str]
    suggestions: list[str]
    details: dict[str, Any]
    created_at: datetime
    resume: ResumeListItem | None = None
    job_description: JobDescriptionListItem | None = None

    model_config = {"from_attributes": True}


class AnalysisListItem(BaseModel):
    id: int
    resume_id: int
    jd_id: int
    overall_score: float
    created_at: datetime
    resume: ResumeListItem | None = None
    job_description: JobDescriptionListItem | None = None

    model_config = {"from_attributes": True}


class RankingItem(BaseModel):
    id: int
    jd_id: int
    resume_id: int
    analysis_id: int | None
    rank: int
    overall_score: float
    resume: ResumeListItem | None = None
    analysis: AnalysisResponse | None = None

    model_config = {"from_attributes": True}


class RankingResponse(BaseModel):
    job_description: JobDescriptionListItem
    rankings: list[RankingItem]
    total: int


class DashboardStats(BaseModel):
    total_resumes: int
    total_jds: int
    total_analyses: int
    avg_score: float
    top_score: float
    recent_analyses: list[AnalysisListItem]


# ── Intelligence / Tailoring Report schemas ───────────────────────────────────

class IntelligenceRequest(BaseModel):
    resume_id: int
    jd_id: int | None = None
    jd_text: str | None = None
    jd_title: str = "Quick Analysis"
    jd_company: str = ""
    mode: str = Field(default="experienced", pattern="^(fresher|experienced)$")


class GapAnalysisResult(BaseModel):
    critical_missing: list[str]
    important_missing: list[str]
    optional_missing: list[str]
    severity_score: int
    severity_label: str
    score_impact: int
    critical_count: int
    important_count: int
    optional_count: int
    summary: str


class RewriteSuggestion(BaseModel):
    type: str
    impact: str
    skill: str | None = None
    current: str | None = None
    suggested: str
    safety: str
    note: str | None = None


class PriorityItem(BaseModel):
    skill: str
    priority: str
    action: str


class RewritesResult(BaseModel):
    skills_section: list[dict[str, Any]]
    project_bullets: list[dict[str, Any]]
    experience_bullets: list[dict[str, Any]]
    priority_list: list[dict[str, Any]]


class ProjectScore(BaseModel):
    name: str
    index: int
    score: float
    breakdown: dict[str, Any]
    recommendation: dict[str, Any]
    text_preview: str


class ProjectRelevanceResult(BaseModel):
    has_projects: bool
    projects: list[ProjectScore]
    average_relevance: float
    top_project: str | None
    portfolio_summary: str


class RecruiterViewResult(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    interview_likelihood: str
    likelihood_reasoning: str
    overall_impression: str
    standout_factors: list[str]
    call_to_action: str


class QualityIssue(BaseModel):
    category: str
    severity: str
    message: str
    fix: str


class QualityAuditResult(BaseModel):
    quality_score: int
    quality_label: str
    issues: list[QualityIssue]
    positive_signals: list[str]
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    issue_count: int


class JDIntelligenceResult(BaseModel):
    critical_requirements: list[str]
    preferred_requirements: list[str]
    technologies: dict[str, list[str]]
    qualifications: dict[str, Any]
    soft_skills: list[str]


class TailoringReportResponse(BaseModel):
    resume_id: int
    jd_id: int
    mode: str
    ats_score: AnalysisResponse
    jd_intelligence: JDIntelligenceResult
    gap_analysis: GapAnalysisResult
    rewrites: RewritesResult
    project_relevance: ProjectRelevanceResult
    recruiter_view: RecruiterViewResult
    quality_audit: QualityAuditResult


# ── Optimizer / new feature schemas ──────────────────────────────────────────

class InterviewProbabilityFactor(BaseModel):
    name: str
    score: float
    weight: str
    description: str


class InterviewProbabilityResult(BaseModel):
    probability: float
    label: str
    factors: list[InterviewProbabilityFactor]
    reasoning: str
    top_strength: str
    main_bottleneck: str


class CompetitivenessResult(BaseModel):
    label: str
    label_key: str
    composite_score: float
    explanation: str
    detailed_factors: dict[str, Any]


class MarketSkillEntry(BaseModel):
    skill: str
    count: int
    percentage: int


class MarketAnalysisResult(BaseModel):
    jd_count: int
    total_unique_skills: int
    top_skills: list[MarketSkillEntry]
    top_languages: list[MarketSkillEntry]
    top_frameworks: list[MarketSkillEntry]
    top_tools: list[MarketSkillEntry]
    top_cloud: list[MarketSkillEntry]
    top_databases: list[MarketSkillEntry]
    top_concepts: list[MarketSkillEntry]
    missing_from_profile: list[dict[str, Any]]
    profile_provided: bool


class VariantResponse(BaseModel):
    id: int
    name: str
    variant_type: str
    resume_id: int | None
    content: dict[str, Any]
    description: str
    created_at: str | None
    updated_at: str | None


# ── Application Tracker schemas ───────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(..., min_length=1, max_length=200)
    date_applied: str = Field(default="")
    status: str = Field(default="applied")
    notes: str = Field(default="")
    variant_id: int | None = None
    jd_id: int | None = None


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    date_applied: str | None = None
    status: str | None = None
    notes: str | None = None
    variant_id: int | None = None
    jd_id: int | None = None


class ApplicationResponse(BaseModel):
    id: int
    company: str
    role: str
    date_applied: str
    status: str
    notes: str
    variant_id: int | None
    jd_id: int | None
    variant_name: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ApplicationAnalytics(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    conversion_rates: dict[str, float]
    variant_performance: list[dict[str, Any]]
    monthly_trend: list[dict[str, Any]]


# ── Cover Letter schema ────────────────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    resume_id: int
    jd_id: int | None = None
    jd_text: str | None = None
    company: str = Field(default="the company")
    mode: str = Field(default="experienced", pattern="^(fresher|experienced)$")


class CoverLetterResult(BaseModel):
    cover_letter_text: str
    paragraphs: dict[str, str]
    word_count: int
    safety_notes: list[str]


# ── Skill Gap Roadmap schemas ──────────────────────────────────────────────────

class RoadmapSkillEntry(BaseModel):
    skill: str
    category: str
    market_demand: int
    priority_score: float
    why: str


class RoadmapPhase(BaseModel):
    phase: int
    label: str
    timeframe: str
    skills: list[RoadmapSkillEntry]


class SkillRoadmapResult(BaseModel):
    phases: list[RoadmapPhase]
    total_skills: int
    total_phases: int
    learning_focus: str
