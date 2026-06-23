const BASE = "/api";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Resumes
export const resumeApi = {
  upload: async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    const res = await fetch(`${BASE}/resumes/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json();
  },
  list: () => request<Resume[]>("/resumes"),
  get: (id: number) => request<Resume>(`/resumes/${id}`),
  delete: (id: number) => request<void>(`/resumes/${id}`, { method: "DELETE" }),
};

// Job Descriptions
export const jdApi = {
  create: (data: { title: string; company?: string; description: string }) =>
    request<JobDescription>("/job-descriptions", { method: "POST", body: JSON.stringify(data) }),
  list: () => request<JobDescriptionListItem[]>("/job-descriptions"),
  get: (id: number) => request<JobDescription>(`/job-descriptions/${id}`),
  update: (id: number, data: Partial<{ title: string; company: string; description: string }>) =>
    request<JobDescription>(`/job-descriptions/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/job-descriptions/${id}`, { method: "DELETE" }),
};

// Analysis
export const analysisApi = {
  run: (data: { resume_id: number; jd_id?: number; jd_text?: string; jd_title?: string; jd_company?: string }) =>
    request<Analysis>("/analysis/run", { method: "POST", body: JSON.stringify(data) }),
  bulk: (data: { resume_ids: number[]; jd_id?: number; jd_text?: string; jd_title?: string; jd_company?: string }) =>
    request<BulkResult>("/analysis/bulk", { method: "POST", body: JSON.stringify(data) }),
  list: (skip = 0, limit = 50) => request<AnalysisListItem[]>(`/analysis?skip=${skip}&limit=${limit}`),
  get: (id: number) => request<Analysis>(`/analysis/${id}`),
  dashboard: () => request<DashboardStats>("/analysis/dashboard"),
  delete: (id: number) => request<void>(`/analysis/${id}`, { method: "DELETE" }),
};

// Rankings
export const rankingApi = {
  get: (jdId: number) => request<RankingResponse>(`/rankings/${jdId}`),
};

// Exports
export const exportApi = {
  pdf: (analysisId: number) => `${BASE}/exports/pdf/${analysisId}`,
  csv: (jdId: number) => `${BASE}/exports/csv/${jdId}`,
};

export const healthApi = {
  check: () => request<{ status: string }>("/health"),
};

// Intelligence / Tailoring Report
export const intelligenceApi = {
  analyze: (data: {
    resume_id: number;
    jd_id?: number;
    jd_text?: string;
    jd_title?: string;
    jd_company?: string;
    mode?: "fresher" | "experienced";
  }) =>
    request<TailoringReport>("/intelligence/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getJdIntelligence: (jdId: number) =>
    request<JDIntelligence>(`/intelligence/jd/${jdId}`),
};

// Types
export interface Resume {
  id: number;
  filename: string;
  original_filename: string;
  file_type: string;
  raw_text?: string;
  parsed_data?: ParsedData;
  created_at: string;
  updated_at: string;
}

export interface ParsedData {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
  github?: string;
  skills?: string[];
  education?: Array<{ degree: string; year?: string }>;
  education_level?: number;
  years_of_experience?: number;
  projects?: string[];
  certifications?: string[];
  word_count?: number;
  sections_detected?: string[];
}

export interface JobDescription {
  id: number;
  title: string;
  company: string;
  description: string;
  parsed_data?: { keywords?: string[]; skills?: string[]; keyword_count?: number };
  created_at: string;
  updated_at: string;
}

export interface JobDescriptionListItem {
  id: number;
  title: string;
  company: string;
  created_at: string;
}

export interface Analysis {
  id: number;
  resume_id: number;
  jd_id: number;
  overall_score: number;
  keyword_score: number;
  skills_score: number;
  experience_score: number;
  education_score: number;
  semantic_score: number;
  missing_keywords: string[];
  missing_skills: string[];
  matched_keywords: string[];
  matched_skills: string[];
  suggestions: string[];
  details: AnalysisDetails;
  created_at: string;
  resume?: { id: number; original_filename: string; file_type: string; created_at: string; parsed_data?: ParsedData };
  job_description?: JobDescriptionListItem;
}

export interface AnalysisDetails {
  jd_keywords_count?: number;
  jd_skills_count?: number;
  resume_skills_count?: number;
  resume_years_experience?: number;
  resume_education_level?: number;
  jd_education_level?: number;
  jd_required_years?: number;
  resume_word_count?: number;
}

export interface AnalysisListItem {
  id: number;
  resume_id: number;
  jd_id: number;
  overall_score: number;
  created_at: string;
  resume?: { id: number; original_filename: string; file_type: string; created_at: string };
  job_description?: JobDescriptionListItem;
}

export interface DashboardStats {
  total_resumes: number;
  total_jds: number;
  total_analyses: number;
  avg_score: number;
  top_score: number;
  recent_analyses: AnalysisListItem[];
}

export interface RankingItem {
  id: number;
  jd_id: number;
  resume_id: number;
  analysis_id?: number;
  rank: number;
  overall_score: number;
  resume?: { id: number; original_filename: string; file_type: string; created_at: string; parsed_data?: ParsedData };
  analysis?: Analysis;
}

export interface RankingResponse {
  job_description: JobDescriptionListItem;
  rankings: RankingItem[];
  total: number;
}

export interface BulkResult {
  jd_id: number;
  analyses: Array<{ resume_id: number; analysis_id: number; score: number }>;
  total: number;
}

// ── Intelligence / Tailoring Report types ─────────────────────────────────────

export interface JDIntelligence {
  critical_requirements: string[];
  preferred_requirements: string[];
  technologies: Record<string, string[]>;
  qualifications: {
    experience: { min_years: number | null; max_years: number | null; description: string; is_entry_level: boolean };
    education: { level: string; description: string };
    certifications: string[];
  };
  soft_skills: string[];
}

export interface GapAnalysis {
  critical_missing: string[];
  important_missing: string[];
  optional_missing: string[];
  severity_score: number;
  severity_label: "LOW" | "MEDIUM" | "HIGH";
  score_impact: number;
  critical_count: number;
  important_count: number;
  optional_count: number;
  summary: string;
}

export interface RewriteSuggestion {
  type: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
  skill?: string;
  current?: string | null;
  suggested: string;
  safety: "SAFE" | "REQUIRES_VERIFICATION";
  note?: string;
}

export interface PriorityItem {
  skill: string;
  priority: "HIGH IMPACT" | "MEDIUM IMPACT" | "LOW IMPACT";
  action: string;
}

export interface Rewrites {
  skills_section: RewriteSuggestion[];
  project_bullets: RewriteSuggestion[];
  experience_bullets: RewriteSuggestion[];
  priority_list: PriorityItem[];
}

export interface ProjectScore {
  name: string;
  index: number;
  score: number;
  breakdown: {
    technical_relevance: number;
    skill_overlap: number;
    keyword_overlap: number;
    semantic_similarity: number;
    matched_skills: string[];
  };
  recommendation: { action: string; detail: string; priority: string };
  text_preview: string;
}

export interface ProjectRelevance {
  has_projects: boolean;
  projects: ProjectScore[];
  average_relevance: number;
  top_project: string | null;
  portfolio_summary: string;
}

export interface RecruiterView {
  strengths: string[];
  weaknesses: string[];
  interview_likelihood: "HIGH" | "MEDIUM" | "LOW" | "VERY LOW";
  likelihood_reasoning: string;
  overall_impression: string;
  standout_factors: string[];
  call_to_action: string;
}

export interface QualityIssue {
  category: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  message: string;
  fix: string;
}

export interface QualityAudit {
  quality_score: number;
  quality_label: string;
  issues: QualityIssue[];
  positive_signals: string[];
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  issue_count: number;
}

export interface TailoringReport {
  resume_id: number;
  jd_id: number;
  mode: "fresher" | "experienced";
  ats_score: Analysis;
  jd_intelligence: JDIntelligence;
  gap_analysis: GapAnalysis;
  rewrites: Rewrites;
  project_relevance: ProjectRelevance;
  recruiter_view: RecruiterView;
  quality_audit: QualityAudit;
}

// ── Optimizer types ────────────────────────────────────────────────────────────

export interface OptimizedSkills {
  primary: string[];
  secondary: string[];
  all: string[];
}

export interface OptimizedEntry {
  original: string;
  optimized: string;
  safety: "SAFE" | "REQUIRES_VERIFICATION";
  start?: string;
  end?: string;
}

export interface OptimizedChange {
  type: "ADDED" | "REMOVED" | "REORDERED" | "REWRITTEN";
  section: string;
  description: string;
  original: string | string[];
  optimized: string | string[];
  safety?: string;
}

export interface OptimizedResume {
  name: string | null;
  contact: { email?: string; phone?: string; linkedin?: string; github?: string };
  section_order: string[];
  skills: OptimizedSkills;
  projects: OptimizedEntry[];
  experience: OptimizedEntry[];
  education: Array<{ degree: string; year?: string }>;
  certifications: string[];
  changes: OptimizedChange[];
  changes_summary: {
    total_changes: number;
    sections_reordered: boolean;
    skills_reordered: boolean;
    projects_reordered: boolean;
    bullets_rewritten: number;
  };
}

export interface ResumeDiff {
  added: OptimizedChange[];
  removed: OptimizedChange[];
  reordered: OptimizedChange[];
  rewritten: OptimizedChange[];
  total_changes: number;
  has_changes: boolean;
  summary: string;
}

export interface InterviewProbabilityFactor {
  name: string;
  score: number;
  weight: string;
  description: string;
}

export interface InterviewProbability {
  probability: number;
  label: "HIGH" | "MEDIUM" | "LOW" | "VERY LOW";
  factors: InterviewProbabilityFactor[];
  reasoning: string;
  top_strength: string;
  main_bottleneck: string;
}

export interface Competitiveness {
  label: string;
  label_key: "STRONG_MATCH" | "REASONABLE_MATCH" | "STRETCH" | "LOW_PROBABILITY";
  composite_score: number;
  explanation: string;
  detailed_factors: Record<string, number>;
}

export interface OptimizationReport {
  resume_id: number;
  jd_id: number;
  mode: "fresher" | "experienced";
  ats_score: Record<string, number>;
  optimized_resume: OptimizedResume;
  diff: ResumeDiff;
  interview_probability: InterviewProbability;
  competitiveness: Competitiveness;
}

// ── Variant types ──────────────────────────────────────────────────────────────

export type VariantType = "master" | "backend" | "fullstack" | "ai" | "custom";

export interface ResumeVariant {
  id: number;
  name: string;
  variant_type: VariantType;
  resume_id: number | null;
  content: Record<string, unknown>;
  description: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface VariantRecommendation {
  recommended: ResumeVariant;
  match_score: number;
  all_scores: Array<{ id: number; name: string; score: number }>;
  reasoning: string;
}

// ── Market analysis types ──────────────────────────────────────────────────────

export interface MarketSkillEntry {
  skill: string;
  count: number;
  percentage: number;
  category?: string;
}

export interface MarketAnalysis {
  jd_count: number;
  total_unique_skills: number;
  top_skills: MarketSkillEntry[];
  top_languages: MarketSkillEntry[];
  top_frameworks: MarketSkillEntry[];
  top_tools: MarketSkillEntry[];
  top_cloud: MarketSkillEntry[];
  top_databases: MarketSkillEntry[];
  top_concepts: MarketSkillEntry[];
  missing_from_profile: MarketSkillEntry[];
  profile_provided: boolean;
}

// ── New API clients ────────────────────────────────────────────────────────────

export const optimizerApi = {
  generate: (data: {
    resume_id: number;
    jd_id?: number;
    jd_text?: string;
    jd_title?: string;
    jd_company?: string;
    mode?: "fresher" | "experienced";
  }) => request<OptimizationReport>("/optimizer/generate", { method: "POST", body: JSON.stringify(data) }),

  exportDocx: async (optimized: OptimizedResume): Promise<Blob> => {
    const res = await fetch(`${BASE}/optimizer/export/docx`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(optimized),
    });
    if (!res.ok) throw new Error("DOCX export failed");
    return res.blob();
  },

  exportPdf: async (optimized: OptimizedResume): Promise<Blob> => {
    const res = await fetch(`${BASE}/optimizer/export/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(optimized),
    });
    if (!res.ok) throw new Error("PDF export failed");
    return res.blob();
  },
};

export const variantsApi = {
  list: () => request<ResumeVariant[]>("/variants"),
  get: (id: number) => request<ResumeVariant>(`/variants/${id}`),
  create: (data: { name: string; variant_type?: VariantType; resume_id?: number; content?: Record<string, unknown>; description?: string }) =>
    request<ResumeVariant>("/variants", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: { name?: string; description?: string; content?: Record<string, unknown>; variant_type?: VariantType }) =>
    request<ResumeVariant>(`/variants/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/variants/${id}`, { method: "DELETE" }),
  duplicate: (id: number) => request<ResumeVariant>(`/variants/${id}/duplicate`, { method: "POST" }),
  recommend: (data: { jd_id?: number; jd_text?: string }) =>
    request<VariantRecommendation>("/variants/recommend", { method: "POST", body: JSON.stringify(data) }),
};

export const marketApi = {
  analyze: (data: { jd_texts?: string[]; jd_ids?: number[]; resume_id?: number }) =>
    request<MarketAnalysis>("/market/analyze", { method: "POST", body: JSON.stringify(data) }),
  roadmap: (data: { missing_skills: MarketSkillEntry[]; resume_id?: number }) =>
    request<SkillRoadmap>("/market/roadmap", { method: "POST", body: JSON.stringify(data) }),
};

// ── Application Tracker ───────────────────────────────────────────────────────

export type ApplicationStatus = "applied" | "phone_screen" | "interview" | "offer" | "rejected" | "withdrawn";

export interface Application {
  id: number;
  company: string;
  role: string;
  date_applied: string;
  status: ApplicationStatus;
  notes: string;
  variant_id: number | null;
  jd_id: number | null;
  variant_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationAnalytics {
  total_applications: number;
  by_status: Record<ApplicationStatus, number>;
  conversion_rates: { response_rate: number; interview_rate: number; offer_rate: number };
  variant_performance: Array<{ variant_id: number; variant_name: string | null; applications: number; interviews: number; offers: number }>;
  monthly_trend: Array<{ month: string; count: number }>;
}

export const applicationsApi = {
  list: (statusFilter?: ApplicationStatus) =>
    request<Application[]>(`/applications${statusFilter ? `?status_filter=${statusFilter}` : ""}`),
  get: (id: number) => request<Application>(`/applications/${id}`),
  create: (data: { company: string; role: string; date_applied?: string; status?: ApplicationStatus; notes?: string; variant_id?: number; jd_id?: number }) =>
    request<Application>("/applications", { method: "POST", body: JSON.stringify(data) }),
  update: (id: number, data: Partial<{ company: string; role: string; date_applied: string; status: ApplicationStatus; notes: string; variant_id: number; jd_id: number }>) =>
    request<Application>(`/applications/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: number) => request<void>(`/applications/${id}`, { method: "DELETE" }),
  analytics: () => request<ApplicationAnalytics>("/applications/analytics"),
};

// ── Cover Letter ──────────────────────────────────────────────────────────────

export interface CoverLetter {
  cover_letter_text: string;
  paragraphs: { opening: string; body_technical: string; body_projects: string; closing: string };
  word_count: number;
  safety_notes: string[];
}

export const coverLetterApi = {
  generate: (data: { resume_id: number; jd_id?: number; jd_text?: string; company?: string; mode?: "fresher" | "experienced" }) =>
    request<CoverLetter>("/optimizer/cover-letter", { method: "POST", body: JSON.stringify(data) }),
};

// ── Skill Roadmap ─────────────────────────────────────────────────────────────

export interface RoadmapSkill {
  skill: string;
  category: string;
  market_demand: number;
  priority_score: number;
  why: string;
}

export interface RoadmapPhase {
  phase: number;
  label: string;
  timeframe: string;
  skills: RoadmapSkill[];
}

export interface SkillRoadmap {
  phases: RoadmapPhase[];
  total_skills: number;
  total_phases: number;
  learning_focus: string;
}

// ── Save-as-variant ───────────────────────────────────────────────────────────

export const saveAsVariantApi = {
  save: (data: { optimized_resume: OptimizedResume; company: string; role: string; date?: string }) =>
    request<ResumeVariant>("/optimizer/save-as-variant", { method: "POST", body: JSON.stringify(data) }),
};
