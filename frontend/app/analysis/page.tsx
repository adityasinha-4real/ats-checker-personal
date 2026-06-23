"use client";
import { useEffect, useState } from "react";
import {
  resumeApi, jdApi, analysisApi, intelligenceApi,
  type Resume, type JobDescriptionListItem, type Analysis, type TailoringReport,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ResumeUploader } from "@/components/custom/ResumeUploader";
import { JobDescriptionInput } from "@/components/custom/JobDescriptionInput";
import { AnalysisResults } from "@/components/custom/AnalysisResults";
import { TailoringReportComponent } from "@/components/custom/TailoringReport";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/use-toast";
import { Loader2, Play, Users, Sparkles } from "lucide-react";
import { exportApi } from "@/lib/api";

type AnalysisMode = "single" | "bulk" | "deep";
type ScoringMode = "experienced" | "fresher";

export default function AnalysisPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [savedJDs, setSavedJDs] = useState<JobDescriptionListItem[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>("");
  const [selectedResumeIds, setSelectedResumeIds] = useState<number[]>([]);
  const [jdId, setJdId] = useState<number | null>(null);
  const [jdText, setJdText] = useState("");
  const [jdTitle, setJdTitle] = useState("Quick Analysis");
  const [jdCompany, setJdCompany] = useState("");
  const [running, setRunning] = useState(false);
  const [bulkRunning, setBulkRunning] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [tailoringResult, setTailoringResult] = useState<TailoringReport | null>(null);
  const [mode, setMode] = useState<AnalysisMode>("single");
  const [scoringMode, setScoringMode] = useState<ScoringMode>("experienced");

  const loadData = async () => {
    const [r, j] = await Promise.all([resumeApi.list(), jdApi.list()]);
    setResumes(r);
    setSavedJDs(j);
  };

  useEffect(() => { loadData(); }, []);

  const handleJDSelected = (id: number | null, text: string, title: string, company: string) => {
    setJdId(id);
    setJdText(text);
    setJdTitle(title || "Quick Analysis");
    setJdCompany(company);
  };

  const runSingle = async () => {
    if (!selectedResumeId) {
      toast({ title: "Select a resume", description: "Choose which resume to analyse.", variant: "destructive" });
      return;
    }
    if (!jdId && !jdText.trim()) {
      toast({ title: "Add a job description", description: "Paste or select a job description.", variant: "destructive" });
      return;
    }
    setRunning(true);
    setResult(null);
    setTailoringResult(null);
    try {
      const analysis = await analysisApi.run({
        resume_id: parseInt(selectedResumeId),
        jd_id: jdId || undefined,
        jd_text: jdId ? undefined : jdText,
        jd_title: jdTitle,
        jd_company: jdCompany,
      });
      setResult(analysis);
      toast({ title: "Analysis complete!", description: `ATS Score: ${analysis.overall_score.toFixed(1)}/100` });
    } catch (err: unknown) {
      toast({ title: "Analysis failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  const runDeep = async () => {
    if (!selectedResumeId) {
      toast({ title: "Select a resume", description: "Choose which resume to analyse.", variant: "destructive" });
      return;
    }
    if (!jdId && !jdText.trim()) {
      toast({ title: "Add a job description", description: "Paste or select a job description.", variant: "destructive" });
      return;
    }
    setRunning(true);
    setResult(null);
    setTailoringResult(null);
    try {
      const report = await intelligenceApi.analyze({
        resume_id: parseInt(selectedResumeId),
        jd_id: jdId || undefined,
        jd_text: jdId ? undefined : jdText,
        jd_title: jdTitle,
        jd_company: jdCompany,
        mode: scoringMode,
      });
      setTailoringResult(report);
      toast({
        title: "Tailoring Report Ready!",
        description: `ATS: ${report.ats_score.overall_score.toFixed(1)}/100 · Quality: ${report.quality_audit.quality_score}/100`,
      });
    } catch (err: unknown) {
      toast({ title: "Analysis failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  const toggleBulkSelect = (id: number) => {
    setSelectedResumeIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const runBulk = async () => {
    if (selectedResumeIds.length === 0) {
      toast({ title: "Select resumes", description: "Choose at least one resume.", variant: "destructive" });
      return;
    }
    if (!jdId && !jdText.trim()) {
      toast({ title: "Add a job description", variant: "destructive" });
      return;
    }
    setBulkRunning(true);
    try {
      const res = await analysisApi.bulk({
        resume_ids: selectedResumeIds,
        jd_id: jdId || undefined,
        jd_text: jdId ? undefined : jdText,
        jd_title: jdTitle,
        jd_company: jdCompany,
      });
      toast({ title: "Bulk analysis complete!", description: `Analysed ${res.total} resumes. View Rankings to see results.` });
      setSelectedResumeIds([]);
    } catch (err: unknown) {
      toast({ title: "Bulk analysis failed", description: err instanceof Error ? err.message : "Unknown error", variant: "destructive" });
    } finally {
      setBulkRunning(false);
    }
  };

  const modeBtn = (m: AnalysisMode, label: React.ReactNode) => (
    <button
      onClick={() => { setMode(m); setResult(null); setTailoringResult(null); }}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
        mode === m ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Resume Analysis</h1>
        <p className="text-muted-foreground mt-1">Upload resumes and analyse them against job descriptions</p>
      </div>

      {/* Mode selector */}
      <div className="flex gap-2 flex-wrap">
        {modeBtn("single", <><Play className="h-3.5 w-3.5" /> Standard</>)}
        {modeBtn("deep", <><Sparkles className="h-3.5 w-3.5" /> Deep Analysis</>)}
        {modeBtn("bulk", <><Users className="h-4 w-4" /> Bulk</>)}
      </div>

      {/* Deep analysis scoring mode */}
      {mode === "deep" && (
        <div className="flex items-center gap-3 bg-purple-50 border border-purple-200 rounded-lg px-4 py-3">
          <span className="text-sm font-medium text-purple-800">Scoring Mode:</span>
          <button
            onClick={() => setScoringMode("experienced")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
              scoringMode === "experienced" ? "bg-blue-600 text-white" : "bg-white text-gray-700 border"
            }`}
          >
            💼 Experienced
          </button>
          <button
            onClick={() => setScoringMode("fresher")}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
              scoringMode === "fresher" ? "bg-purple-600 text-white" : "bg-white text-gray-700 border"
            }`}
          >
            🎓 Fresher / Student
          </button>
          <span className="text-xs text-purple-700">
            {scoringMode === "fresher"
              ? "Reduces experience penalty · boosts skills & projects weight"
              : "Standard weights: keywords 35%, skills 25%, experience 15%"}
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">1. Upload Resumes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ResumeUploader onUploaded={() => loadData()} />
            <Separator />
            {mode !== "bulk" ? (
              <div>
                <Label>Select resume to analyse</Label>
                <Select value={selectedResumeId} onValueChange={setSelectedResumeId}>
                  <SelectTrigger>
                    <SelectValue placeholder={resumes.length === 0 ? "Upload a resume first" : "Choose resume..."} />
                  </SelectTrigger>
                  <SelectContent>
                    {resumes.map((r) => (
                      <SelectItem key={r.id} value={String(r.id)}>
                        {r.original_filename}
                        {r.parsed_data?.name ? ` (${r.parsed_data.name})` : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div>
                <Label className="mb-2 block">Select resumes for bulk analysis</Label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {resumes.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No resumes uploaded yet</p>
                  ) : (
                    resumes.map((r) => (
                      <label key={r.id} className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-muted/30">
                        <input
                          type="checkbox"
                          checked={selectedResumeIds.includes(r.id)}
                          onChange={() => toggleBulkSelect(r.id)}
                          className="rounded"
                        />
                        <span className="text-sm truncate">{r.original_filename}</span>
                      </label>
                    ))
                  )}
                </div>
                {selectedResumeIds.length > 0 && (
                  <p className="text-xs text-blue-600 mt-2">{selectedResumeIds.length} resume(s) selected</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* JD Section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">2. Job Description</CardTitle>
          </CardHeader>
          <CardContent>
            <JobDescriptionInput
              savedJDs={savedJDs}
              onJDSelected={handleJDSelected}
              onSaved={loadData}
            />
          </CardContent>
        </Card>
      </div>

      {/* Run Buttons */}
      {mode === "single" && (
        <Button onClick={runSingle} disabled={running} size="lg" className="w-full sm:w-auto">
          {running ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Analysing...</> : <><Play className="h-4 w-4 mr-2" /> Run ATS Analysis</>}
        </Button>
      )}

      {mode === "deep" && (
        <Button onClick={runDeep} disabled={running} size="lg" className="w-full sm:w-auto bg-purple-600 hover:bg-purple-700">
          {running
            ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running Deep Analysis...</>
            : <><Sparkles className="h-4 w-4 mr-2" /> Generate Full Tailoring Report</>}
        </Button>
      )}

      {mode === "bulk" && (
        <Button onClick={runBulk} disabled={bulkRunning} size="lg" className="w-full sm:w-auto">
          {bulkRunning
            ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Running Bulk Analysis...</>
            : <><Users className="h-4 w-4 mr-2" /> Run Bulk Analysis ({selectedResumeIds.length})</>}
        </Button>
      )}

      {/* Standard results */}
      {result && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Analysis Results</h2>
            <a
              href={exportApi.pdf(result.id)}
              download
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border bg-background hover:bg-accent transition-colors"
            >
              Export PDF
            </a>
          </div>
          <AnalysisResults analysis={result} />
        </div>
      )}

      {/* Deep analysis tailoring report */}
      {tailoringResult && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Full Tailoring Report</h2>
          <TailoringReportComponent report={tailoringResult} />
        </div>
      )}
    </div>
  );
}
