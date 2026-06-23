"use client";
import { type TailoringReport, type RewriteSuggestion } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { AnalysisResults } from "@/components/custom/AnalysisResults";
import { exportApi } from "@/lib/api";

interface Props {
  report: TailoringReport;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function severityColor(sev: string) {
  if (sev === "HIGH") return "bg-red-100 text-red-700 border-red-200";
  if (sev === "MEDIUM") return "bg-yellow-100 text-yellow-700 border-yellow-200";
  return "bg-green-100 text-green-700 border-green-200";
}

function likelihoodColor(l: string) {
  if (l === "HIGH") return "text-green-700 bg-green-50 border border-green-200";
  if (l === "MEDIUM") return "text-yellow-700 bg-yellow-50 border border-yellow-200";
  return "text-red-700 bg-red-50 border border-red-200";
}

function impactBadge(impact: string) {
  if (impact === "HIGH") return "bg-red-100 text-red-700";
  if (impact === "MEDIUM") return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 75 ? "bg-green-100 text-green-800" :
    score >= 50 ? "bg-yellow-100 text-yellow-800" :
    "bg-red-100 text-red-800";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${color}`}>
      {score.toFixed(0)}/100
    </span>
  );
}

// ── Section: JD Intelligence ──────────────────────────────────────────────────

function JDIntelligencePanel({ intel }: { intel: TailoringReport["jd_intelligence"] }) {
  const { qualifications, technologies } = intel;
  const techEntries = Object.entries(technologies).filter(([, v]) => v.length > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          🔍 JD Intelligence
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">Critical Requirements</p>
            <div className="flex flex-wrap gap-1">
              {intel.critical_requirements.length === 0 ? (
                <span className="text-xs text-muted-foreground">None detected</span>
              ) : intel.critical_requirements.map(r => (
                <Badge key={r} className="bg-red-100 text-red-800 hover:bg-red-100 text-xs">{r}</Badge>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-2">Preferred Requirements</p>
            <div className="flex flex-wrap gap-1">
              {intel.preferred_requirements.length === 0 ? (
                <span className="text-xs text-muted-foreground">None detected</span>
              ) : intel.preferred_requirements.map(r => (
                <Badge key={r} className="bg-blue-100 text-blue-800 hover:bg-blue-100 text-xs">{r}</Badge>
              ))}
            </div>
          </div>
        </div>

        <Separator />

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="p-2 rounded-lg bg-muted/40">
            <p className="text-xs text-muted-foreground">Experience Required</p>
            <p className="font-medium text-sm">{qualifications.experience.description}</p>
          </div>
          <div className="p-2 rounded-lg bg-muted/40">
            <p className="text-xs text-muted-foreground">Education</p>
            <p className="font-medium text-sm">{qualifications.education.description}</p>
          </div>
          {qualifications.certifications.length > 0 && (
            <div className="p-2 rounded-lg bg-muted/40">
              <p className="text-xs text-muted-foreground">Certifications</p>
              <p className="font-medium text-sm">{qualifications.certifications.slice(0, 2).join(", ")}</p>
            </div>
          )}
        </div>

        {techEntries.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Tech Stack Breakdown</p>
            <div className="space-y-1.5">
              {techEntries.map(([cat, skills]) => (
                <div key={cat} className="flex items-start gap-2">
                  <span className="text-xs text-muted-foreground w-24 shrink-0 capitalize pt-0.5">{cat.replace("_", " ")}</span>
                  <div className="flex flex-wrap gap-1">
                    {skills.map(s => (
                      <span key={s} className="text-xs bg-gray-100 rounded px-1.5 py-0.5">{s}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Section: Gap Analysis ─────────────────────────────────────────────────────

function GapAnalysisPanel({ gap }: { gap: TailoringReport["gap_analysis"] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>🎯 Critical Gap Analysis</span>
          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${severityColor(gap.severity_label)}`}>
            {gap.severity_label} SEVERITY
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{gap.summary}</p>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span>Gap Severity</span>
            <span className="font-medium">{gap.severity_score}/100</span>
          </div>
          <Progress value={gap.severity_score} className="h-2" />
        </div>

        {gap.score_impact > 0 && (
          <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1">
            Estimated ATS score reduction from gaps: ~{gap.score_impact} points
          </p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <p className="text-xs font-semibold text-red-600 mb-1.5">🔴 Critical Missing ({gap.critical_count})</p>
            {gap.critical_missing.length === 0 ? (
              <p className="text-xs text-green-600">None — great coverage!</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {gap.critical_missing.map(s => (
                  <Badge key={s} className="bg-red-100 text-red-800 hover:bg-red-100 text-xs">{s}</Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-yellow-700 mb-1.5">🟡 Important Missing ({gap.important_count})</p>
            {gap.important_missing.length === 0 ? (
              <p className="text-xs text-green-600">None</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {gap.important_missing.map(s => (
                  <Badge key={s} className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100 text-xs">{s}</Badge>
                ))}
              </div>
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-1.5">⚪ Optional Missing ({gap.optional_count})</p>
            {gap.optional_missing.length === 0 ? (
              <p className="text-xs text-green-600">None</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {gap.optional_missing.slice(0, 8).map(s => (
                  <Badge key={s} variant="outline" className="text-xs">{s}</Badge>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Section: Recruiter View ───────────────────────────────────────────────────

function RecruiterViewPanel({ rv }: { rv: TailoringReport["recruiter_view"] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>👔 Recruiter View</span>
          <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${likelihoodColor(rv.interview_likelihood)}`}>
            {rv.interview_likelihood} Interview Likelihood
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm italic text-muted-foreground">&ldquo;{rv.overall_impression}&rdquo;</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-2">✅ Strengths</p>
            <ul className="space-y-1">
              {rv.strengths.map((s, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5">
                  <span className="text-green-500 mt-0.5">•</span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-2">❌ Weaknesses</p>
            <ul className="space-y-1">
              {rv.weaknesses.length === 0 ? (
                <li className="text-sm text-green-600">No significant weaknesses detected</li>
              ) : rv.weaknesses.map((w, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5">
                  <span className="text-red-400 mt-0.5">•</span>
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-xs font-semibold text-blue-700 mb-1">Reasoning</p>
          <p className="text-sm text-blue-800">{rv.likelihood_reasoning}</p>
        </div>

        <div className="bg-gray-50 border rounded-lg p-3">
          <p className="text-xs font-semibold text-gray-700 mb-1">💡 Action</p>
          <p className="text-sm">{rv.call_to_action}</p>
        </div>

        {rv.standout_factors.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-purple-700 mb-1.5">⭐ Standout Factors</p>
            <div className="flex flex-wrap gap-1.5">
              {rv.standout_factors.map((f, i) => (
                <span key={i} className="text-xs bg-purple-100 text-purple-800 rounded-full px-2 py-0.5">{f}</span>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Section: Quality Audit ────────────────────────────────────────────────────

function QualityAuditPanel({ quality }: { quality: TailoringReport["quality_audit"] }) {
  const qualColor =
    quality.quality_score >= 85 ? "text-green-700" :
    quality.quality_score >= 70 ? "text-blue-700" :
    quality.quality_score >= 50 ? "text-yellow-700" :
    "text-red-700";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>📋 Resume Quality Audit</span>
          <span className={`text-lg font-bold ${qualColor}`}>
            {quality.quality_score}/100 <span className="text-xs font-medium">{quality.quality_label}</span>
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={quality.quality_score} className="h-2" />

        {quality.positive_signals.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-green-700 mb-1.5">✅ Positive Signals</p>
            <div className="flex flex-wrap gap-1.5">
              {quality.positive_signals.map((s, i) => (
                <span key={i} className="text-xs bg-green-100 text-green-800 rounded-full px-2 py-0.5">{s}</span>
              ))}
            </div>
          </div>
        )}

        {quality.issues.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">Issues Found ({quality.issue_count})</p>
            <div className="space-y-2">
              {quality.issues.map((issue, i) => (
                <div key={i} className={`rounded-lg p-2.5 border ${severityColor(issue.severity)}`}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium">{issue.message}</p>
                    <span className={`text-xs shrink-0 font-semibold px-1.5 py-0.5 rounded ${
                      issue.severity === "HIGH" ? "bg-red-200 text-red-800" :
                      issue.severity === "MEDIUM" ? "bg-yellow-200 text-yellow-800" :
                      "bg-gray-200 text-gray-700"
                    }`}>{issue.severity}</span>
                  </div>
                  <p className="text-xs mt-1 opacity-80">Fix: {issue.fix}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Section: Project Relevance ────────────────────────────────────────────────

function ProjectRelevancePanel({ proj }: { proj: TailoringReport["project_relevance"] }) {
  if (!proj.has_projects) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">📁 Project Relevance</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded p-3">
            {proj.portfolio_summary}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>📁 Project Relevance</span>
          <span className="text-xs text-muted-foreground">Avg: {proj.average_relevance.toFixed(0)}/100</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{proj.portfolio_summary}</p>
        {proj.projects.map((p, i) => (
          <div key={i} className="border rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium text-sm">{p.name}</p>
              <div className="flex items-center gap-2">
                <ScoreBadge score={p.score} />
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                  p.recommendation.action === "MOVE UP" ? "bg-green-100 text-green-700" :
                  p.recommendation.action === "EXPAND" ? "bg-blue-100 text-blue-700" :
                  p.recommendation.action === "MOVE DOWN" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {p.recommendation.action}
                </span>
              </div>
            </div>
            <Progress value={p.score} className="h-1.5" />
            <p className="text-xs text-muted-foreground">{p.recommendation.detail}</p>
            {p.breakdown.matched_skills.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {p.breakdown.matched_skills.map(s => (
                  <span key={s} className="text-xs bg-green-100 text-green-700 rounded px-1.5 py-0.5">{s}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ── Section: Smart Rewrites ───────────────────────────────────────────────────

function RewritesPanel({ rewrites }: { rewrites: TailoringReport["rewrites"] }) {
  const allSuggestions: RewriteSuggestion[] = [
    ...rewrites.skills_section,
    ...rewrites.project_bullets,
    ...rewrites.experience_bullets,
  ];

  if (allSuggestions.length === 0 && rewrites.priority_list.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">✏️ Smart Rewrite Suggestions</CardTitle></CardHeader>
      <CardContent className="space-y-4">

        {/* Priority list */}
        {rewrites.priority_list.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Priority Action List</p>
            <div className="space-y-1.5">
              {rewrites.priority_list.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className={`text-xs shrink-0 px-1.5 py-0.5 rounded font-medium mt-0.5 ${impactBadge(item.priority.split(" ")[0])}`}>
                    {item.priority}
                  </span>
                  <span>{item.action}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Individual suggestions */}
        {allSuggestions.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">Detailed Suggestions</p>
            <div className="space-y-3">
              {allSuggestions.slice(0, 10).map((s, i) => (
                <div key={i} className="border rounded-lg p-3 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${impactBadge(s.impact)}`}>{s.impact} IMPACT</span>
                    <span className="text-xs text-muted-foreground capitalize">{s.type.replace(/_/g, " ")}</span>
                    {s.safety === "SAFE" ? (
                      <span className="text-xs text-green-700 bg-green-100 px-1.5 py-0.5 rounded">✅ SAFE</span>
                    ) : (
                      <span className="text-xs text-yellow-700 bg-yellow-100 px-1.5 py-0.5 rounded">⚠️ VERIFY</span>
                    )}
                    {s.skill && <span className="text-xs font-medium text-blue-700">{s.skill}</span>}
                  </div>
                  {s.current && (
                    <div className="bg-red-50 border border-red-100 rounded p-2">
                      <p className="text-xs text-red-600 font-medium mb-0.5">Current:</p>
                      <p className="text-xs text-red-800">{s.current}</p>
                    </div>
                  )}
                  <div className="bg-green-50 border border-green-100 rounded p-2">
                    <p className="text-xs text-green-600 font-medium mb-0.5">Suggested:</p>
                    <p className="text-xs text-green-800">{s.suggested}</p>
                  </div>
                  {s.note && <p className="text-xs text-muted-foreground italic">{s.note}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function TailoringReportComponent({ report }: Props) {
  const { ats_score, jd_intelligence, gap_analysis, rewrites, project_relevance, recruiter_view, quality_audit } = report;

  return (
    <div className="space-y-6">
      {/* Header banner */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${
            report.mode === "fresher"
              ? "bg-purple-100 text-purple-700 border-purple-200"
              : "bg-blue-100 text-blue-700 border-blue-200"
          }`}>
            {report.mode === "fresher" ? "🎓 Fresher Mode" : "💼 Experienced Mode"}
          </span>
          <span className="text-sm text-muted-foreground">Full Tailoring Report</span>
        </div>
        <a
          href={exportApi.pdf(ats_score.id)}
          download
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border bg-background hover:bg-accent transition-colors"
        >
          Export PDF
        </a>
      </div>

      {/* ATS Score (existing component) */}
      <AnalysisResults analysis={ats_score} />

      {/* New enhanced panels */}
      <JDIntelligencePanel intel={jd_intelligence} />
      <GapAnalysisPanel gap={gap_analysis} />
      <RecruiterViewPanel rv={recruiter_view} />
      <QualityAuditPanel quality={quality_audit} />
      <ProjectRelevancePanel proj={project_relevance} />
      <RewritesPanel rewrites={rewrites} />
    </div>
  );
}
