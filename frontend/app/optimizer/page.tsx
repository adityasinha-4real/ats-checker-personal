"use client";
import { useEffect, useState } from "react";
import {
  resumeApi, jdApi, optimizerApi,
  type Resume, type JobDescriptionListItem,
  type OptimizationReport, type OptimizedResume,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ResumeUploader } from "@/components/custom/ResumeUploader";
import { JobDescriptionInput } from "@/components/custom/JobDescriptionInput";
import { toast } from "@/components/ui/use-toast";
import { Loader2, Wand2, Download, FileText, Diff, BarChart3, ChevronDown, ChevronRight } from "lucide-react";

type ScoringMode = "experienced" | "fresher";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ProbabilityGauge({ probability, label }: { probability: number; label: string }) {
  const color = label === "HIGH" ? "bg-green-500" : label === "MEDIUM" ? "bg-blue-500" : label === "LOW" ? "bg-orange-500" : "bg-red-500";
  const textColor = label === "HIGH" ? "text-green-700" : label === "MEDIUM" ? "text-blue-700" : label === "LOW" ? "text-orange-700" : "text-red-700";
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium">Interview Probability</span>
        <span className={`text-2xl font-bold ${textColor}`}>{probability.toFixed(0)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div className={`${color} h-3 rounded-full transition-all`} style={{ width: `${probability}%` }} />
      </div>
      <Badge className={`${color} text-white`}>{label}</Badge>
    </div>
  );
}

function CompetitivenessCard({ label, label_key, composite_score, explanation }: {
  label: string; label_key: string; composite_score: number; explanation: string;
}) {
  const styles: Record<string, string> = {
    STRONG_MATCH: "bg-green-50 border-green-300 text-green-800",
    REASONABLE_MATCH: "bg-blue-50 border-blue-300 text-blue-800",
    STRETCH: "bg-orange-50 border-orange-300 text-orange-800",
    LOW_PROBABILITY: "bg-red-50 border-red-300 text-red-800",
  };
  const cls = styles[label_key] || "bg-gray-50 border-gray-300 text-gray-800";
  return (
    <div className={`border rounded-lg p-4 ${cls}`}>
      <div className="flex justify-between items-center mb-2">
        <span className="font-semibold text-base">{label}</span>
        <span className="font-bold text-lg">{composite_score.toFixed(0)}/100</span>
      </div>
      <p className="text-sm">{explanation}</p>
    </div>
  );
}

function DiffPanel({ diff }: { diff: OptimizationReport["diff"] }) {
  if (!diff.has_changes) return <p className="text-sm text-muted-foreground">No changes from the optimizer.</p>;
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">{diff.summary}</p>
      {diff.reordered.map((c, i) => (
        <div key={i} className="border-l-4 border-blue-400 pl-3 py-1">
          <span className="text-xs font-bold text-blue-600 uppercase">REORDERED</span>
          <p className="text-sm font-medium">{c.description}</p>
        </div>
      ))}
      {diff.rewritten.map((c, i) => (
        <div key={i} className="border-l-4 border-purple-400 pl-3 py-1">
          <span className="text-xs font-bold text-purple-600 uppercase">REWRITTEN · {(c as { safety?: string }).safety || "SAFE"}</span>
          <p className="text-sm text-muted-foreground line-through">{String(c.original).slice(0, 100)}</p>
          <p className="text-sm font-medium">{String(c.optimized).slice(0, 100)}</p>
        </div>
      ))}
      {diff.added.map((c, i) => (
        <div key={i} className="border-l-4 border-green-400 pl-3 py-1">
          <span className="text-xs font-bold text-green-600 uppercase">ADDED</span>
          <p className="text-sm">{c.description}</p>
        </div>
      ))}
      {diff.removed.map((c, i) => (
        <div key={i} className="border-l-4 border-red-400 pl-3 py-1">
          <span className="text-xs font-bold text-red-600 uppercase">REMOVED</span>
          <p className="text-sm">{c.description}</p>
        </div>
      ))}
    </div>
  );
}

function OptimizedResumePreview({ optimized }: { optimized: OptimizedResume }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="border rounded-lg">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen(!open)}
      >
        <span className="font-semibold">Optimized Resume Preview</span>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-4">
          <div>
            <h3 className="font-bold text-lg">{optimized.name || "Candidate"}</h3>
            <p className="text-sm text-muted-foreground">
              {[optimized.contact.email, optimized.contact.phone, optimized.contact.linkedin].filter(Boolean).join(" · ")}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Section Order</p>
            <div className="flex flex-wrap gap-1">
              {optimized.section_order.map((s, i) => (
                <Badge key={s} variant="outline">
                  {i + 1}. {s}
                </Badge>
              ))}
            </div>
          </div>
          {optimized.skills.all.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1">KEY SKILLS</p>
              <div className="flex flex-wrap gap-1">
                {optimized.skills.primary.map(s => (
                  <Badge key={s} className="bg-blue-100 text-blue-800 text-xs">{s}</Badge>
                ))}
                {optimized.skills.secondary.map(s => (
                  <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                ))}
              </div>
            </div>
          )}
          {optimized.projects.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground mb-1">PROJECTS (reordered by relevance)</p>
              <ul className="space-y-1">
                {optimized.projects.map((p, i) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <span className="text-muted-foreground">•</span>
                    <span>
                      {p.optimized}
                      {p.safety === "REQUIRES_VERIFICATION" && (
                        <span className="ml-1 text-xs text-orange-600 font-medium">[VERIFY]</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function OptimizerPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [savedJDs, setSavedJDs] = useState<JobDescriptionListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [jdId, setJdId] = useState<number | null>(null);
  const [jdText, setJdText] = useState("");
  const [jdTitle, setJdTitle] = useState("Quick Analysis");
  const [jdCompany, setJdCompany] = useState("");
  const [scoringMode, setScoringMode] = useState<ScoringMode>("experienced");
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<OptimizationReport | null>(null);
  const [exporting, setExporting] = useState<"docx" | "pdf" | null>(null);
  const [activeTab, setActiveTab] = useState<"preview" | "diff" | "probability" | "competitiveness">("preview");

  const loadData = async () => {
    const [r, j] = await Promise.all([resumeApi.list(), jdApi.list()]);
    setResumes(r);
    setSavedJDs(j);
  };
  useEffect(() => { loadData(); }, []);

  const handleJDSelected = (id: number | null, text: string, title: string, company: string) => {
    setJdId(id); setJdText(text);
    setJdTitle(title || "Quick Analysis"); setJdCompany(company);
  };

  const runOptimizer = async () => {
    if (!selectedResumeId) {
      toast({ title: "Select a resume", variant: "destructive" }); return;
    }
    if (!jdId && !jdText.trim()) {
      toast({ title: "Add a job description", variant: "destructive" }); return;
    }
    setRunning(true);
    setReport(null);
    try {
      const result = await optimizerApi.generate({
        resume_id: parseInt(selectedResumeId),
        jd_id: jdId || undefined,
        jd_text: jdId ? undefined : jdText,
        jd_title: jdTitle,
        jd_company: jdCompany,
        mode: scoringMode,
      });
      setReport(result);
      toast({ title: "Optimization complete!", description: `${result.diff.total_changes} changes made. Interview probability: ${result.interview_probability.label}` });
    } catch (err: unknown) {
      toast({ title: "Optimization failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  const handleExport = async (format: "docx" | "pdf") => {
    if (!report) return;
    setExporting(format);
    try {
      const blob = format === "docx"
        ? await optimizerApi.exportDocx(report.optimized_resume)
        : await optimizerApi.exportPdf(report.optimized_resume);
      downloadBlob(blob, `optimized_resume.${format}`);
      toast({ title: `${format.toUpperCase()} downloaded` });
    } catch (err: unknown) {
      toast({ title: `${format.toUpperCase()} export failed`, variant: "destructive" });
    } finally {
      setExporting(null);
    }
  };

  const tabBtn = (id: typeof activeTab, label: string) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === id ? "bg-purple-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Resume Optimizer</h1>
        <p className="text-muted-foreground mt-1">Generate a tailored resume draft optimized for the target role</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base">1. Select Resume</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <ResumeUploader onUploaded={loadData} />
            <div>
              <Label>Resume to optimize</Label>
              <Select value={selectedResumeId} onValueChange={setSelectedResumeId}>
                <SelectTrigger>
                  <SelectValue placeholder={resumes.length === 0 ? "Upload a resume first" : "Choose resume..."} />
                </SelectTrigger>
                <SelectContent>
                  {resumes.map(r => (
                    <SelectItem key={r.id} value={String(r.id)}>
                      {r.original_filename}{r.parsed_data?.name ? ` (${r.parsed_data.name})` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">2. Target Job Description</CardTitle></CardHeader>
          <CardContent>
            <JobDescriptionInput savedJDs={savedJDs} onJDSelected={handleJDSelected} onSaved={loadData} />
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-3 bg-purple-50 border border-purple-200 rounded-lg px-4 py-3">
        <span className="text-sm font-medium text-purple-800">Scoring Mode:</span>
        {(["experienced", "fresher"] as ScoringMode[]).map(m => (
          <button
            key={m}
            onClick={() => setScoringMode(m)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${scoringMode === m ? (m === "fresher" ? "bg-purple-600 text-white" : "bg-blue-600 text-white") : "bg-white text-gray-700 border"}`}
          >
            {m === "fresher" ? "🎓 Fresher / Student" : "💼 Experienced"}
          </button>
        ))}
      </div>

      <Button onClick={runOptimizer} disabled={running} size="lg" className="w-full sm:w-auto bg-purple-600 hover:bg-purple-700">
        {running
          ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Optimizing Resume...</>
          : <><Wand2 className="h-4 w-4 mr-2" /> Generate Optimized Resume</>}
      </Button>

      {report && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardContent className="pt-4">
                <ProbabilityGauge
                  probability={report.interview_probability.probability}
                  label={report.interview_probability.label}
                />
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <CompetitivenessCard
                  label={report.competitiveness.label}
                  label_key={report.competitiveness.label_key}
                  composite_score={report.competitiveness.composite_score}
                  explanation={report.competitiveness.explanation}
                />
              </CardContent>
            </Card>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              {tabBtn("preview", "Preview")}
              {tabBtn("diff", `Diff (${report.diff.total_changes})`)}
              {tabBtn("probability", "Probability")}
              {tabBtn("competitiveness", "Match")}
            </div>
            <div className="flex gap-2">
              <Button
                size="sm" variant="outline"
                onClick={() => handleExport("docx")}
                disabled={exporting !== null}
              >
                {exporting === "docx" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5 mr-1" />}
                DOCX
              </Button>
              <Button
                size="sm" variant="outline"
                onClick={() => handleExport("pdf")}
                disabled={exporting !== null}
              >
                {exporting === "pdf" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5 mr-1" />}
                PDF
              </Button>
            </div>
          </div>

          <Card>
            <CardContent className="pt-4">
              {activeTab === "preview" && <OptimizedResumePreview optimized={report.optimized_resume} />}

              {activeTab === "diff" && (
                <div>
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <Diff className="h-4 w-4" /> Resume Diff
                  </h3>
                  <DiffPanel diff={report.diff} />
                </div>
              )}

              {activeTab === "probability" && (
                <div className="space-y-4">
                  <h3 className="font-semibold">Interview Probability Breakdown</h3>
                  <p className="text-sm text-muted-foreground">{report.interview_probability.reasoning}</p>
                  <div className="space-y-3">
                    {report.interview_probability.factors.map(f => (
                      <div key={f.name}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium">{f.name} <span className="text-muted-foreground text-xs">({f.weight})</span></span>
                          <span className="font-bold">{f.score.toFixed(0)}/100</span>
                        </div>
                        <Progress value={f.score} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-0.5">{f.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "competitiveness" && (
                <div className="space-y-4">
                  <h3 className="font-semibold">Competitiveness Analysis</h3>
                  <CompetitivenessCard
                    label={report.competitiveness.label}
                    label_key={report.competitiveness.label_key}
                    composite_score={report.competitiveness.composite_score}
                    explanation={report.competitiveness.explanation}
                  />
                  <div className="grid grid-cols-2 gap-3 mt-4">
                    {Object.entries(report.competitiveness.detailed_factors).map(([k, v]) => (
                      <div key={k} className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-muted-foreground capitalize">{k.replace(/_/g, " ")}</p>
                        <p className="text-lg font-bold">{typeof v === "number" ? v.toFixed(1) : v}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
