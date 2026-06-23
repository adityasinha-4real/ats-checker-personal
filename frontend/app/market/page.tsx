"use client";
import { useEffect, useState } from "react";
import {
  marketApi, resumeApi, jdApi,
  type MarketAnalysis, type MarketSkillEntry, type Resume, type JobDescriptionListItem,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/use-toast";
import { Loader2, BarChart3, TrendingUp, Plus, X, AlertTriangle } from "lucide-react";

function SkillBar({ entry, maxCount }: { entry: MarketSkillEntry; maxCount: number }) {
  const pct = maxCount > 0 ? (entry.count / maxCount) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm w-28 truncate font-medium">{entry.skill}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
        <div
          className="bg-blue-500 h-5 rounded-full flex items-center px-2 transition-all"
          style={{ width: `${Math.max(pct, 4)}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground w-12 text-right">
        {entry.percentage}% · {entry.count}
      </span>
    </div>
  );
}

function SkillSection({ title, skills, color = "blue" }: { title: string; skills: MarketSkillEntry[]; color?: string }) {
  if (skills.length === 0) return null;
  const maxCount = Math.max(...skills.map(s => s.count), 1);
  const barColors: Record<string, string> = {
    blue: "bg-blue-500", green: "bg-green-500", purple: "bg-purple-500",
    orange: "bg-orange-500", red: "bg-red-500", teal: "bg-teal-500",
  };
  const bar = barColors[color] || "bg-blue-500";
  return (
    <div>
      <h3 className="font-semibold text-sm mb-2">{title}</h3>
      <div className="space-y-2">
        {skills.map(s => (
          <div key={s.skill} className="flex items-center gap-3">
            <span className="text-sm w-28 truncate font-medium">{s.skill}</span>
            <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
              <div
                className={`${bar} h-4 rounded-full transition-all`}
                style={{ width: `${Math.max((s.count / maxCount) * 100, 3)}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-14 text-right">
              {s.percentage}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MarketPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [savedJDs, setSavedJDs] = useState<JobDescriptionListItem[]>([]);
  const [selectedJdIds, setSelectedJdIds] = useState<string[]>([]);
  const [pastedJDs, setPastedJDs] = useState<string[]>([""]);
  const [resumeId, setResumeId] = useState("");
  const [analysis, setAnalysis] = useState<MarketAnalysis | null>(null);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "breakdown" | "gaps">("overview");

  useEffect(() => {
    Promise.all([resumeApi.list(), jdApi.list()]).then(([r, j]) => {
      setResumes(r); setSavedJDs(j);
    });
  }, []);

  const toggleJd = (id: string) => {
    setSelectedJdIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const addPastedJD = () => setPastedJDs(prev => [...prev, ""]);
  const removePastedJD = (i: number) => setPastedJDs(prev => prev.filter((_, idx) => idx !== i));
  const updatePastedJD = (i: number, val: string) => setPastedJDs(prev => prev.map((p, idx) => idx === i ? val : p));

  const runAnalysis = async () => {
    const jd_ids = selectedJdIds.map(Number);
    const jd_texts = pastedJDs.filter(t => t.trim().length > 20);
    if (jd_ids.length === 0 && jd_texts.length === 0) {
      toast({ title: "Add at least one JD", variant: "destructive" }); return;
    }
    setRunning(true);
    setAnalysis(null);
    try {
      const result = await marketApi.analyze({
        jd_ids,
        jd_texts,
        resume_id: resumeId ? parseInt(resumeId) : undefined,
      });
      setAnalysis(result);
      toast({ title: `Market analyzed`, description: `${result.jd_count} JDs · ${result.total_unique_skills} unique skills found` });
    } catch (err: unknown) {
      toast({ title: "Analysis failed", description: err instanceof Error ? err.message : "", variant: "destructive" });
    } finally { setRunning(false); }
  };

  const tabBtn = (id: typeof activeTab, label: string) => (
    <button
      onClick={() => setActiveTab(id)}
      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === id ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="p-8 space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Market Analyzer</h1>
        <p className="text-muted-foreground mt-1">Analyze multiple job descriptions to find the most in-demand skills</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Select Saved JDs</CardTitle></CardHeader>
          <CardContent>
            {savedJDs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No saved JDs yet. Use the paste option below.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {savedJDs.map(j => (
                  <label key={j.id} className="flex items-center gap-2 p-2 rounded border cursor-pointer hover:bg-muted/30">
                    <input
                      type="checkbox"
                      checked={selectedJdIds.includes(String(j.id))}
                      onChange={() => toggleJd(String(j.id))}
                      className="rounded"
                    />
                    <span className="text-sm">{j.title} — {j.company || "No company"}</span>
                  </label>
                ))}
              </div>
            )}
            {selectedJdIds.length > 0 && (
              <p className="text-xs text-blue-600 mt-2">{selectedJdIds.length} JD(s) selected</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Paste Additional JDs</CardTitle>
              <Button size="sm" variant="outline" onClick={addPastedJD}>
                <Plus className="h-3.5 w-3.5 mr-1" /> Add JD
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {pastedJDs.map((text, i) => (
              <div key={i} className="flex gap-2">
                <textarea
                  className="flex-1 border rounded-md px-3 py-2 text-sm min-h-[60px] resize-none"
                  placeholder={`Job description ${i + 1}...`}
                  value={text}
                  onChange={e => updatePastedJD(i, e.target.value)}
                />
                {pastedJDs.length > 1 && (
                  <Button size="sm" variant="ghost" onClick={() => removePastedJD(i)} className="h-8 w-8 p-0 text-red-500">
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Compare Against Resume Profile (optional)</CardTitle></CardHeader>
        <CardContent>
          <Select value={resumeId} onValueChange={setResumeId}>
            <SelectTrigger className="max-w-sm">
              <SelectValue placeholder="Select your resume to find gaps..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">No resume (analysis only)</SelectItem>
              {resumes.map(r => (
                <SelectItem key={r.id} value={String(r.id)}>
                  {r.original_filename}{r.parsed_data?.name ? ` (${r.parsed_data.name})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Button onClick={runAnalysis} disabled={running} size="lg">
        {running
          ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Analyzing Market...</>
          : <><BarChart3 className="h-4 w-4 mr-2" /> Analyze Market</>}
      </Button>

      {analysis && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-blue-700">{analysis.jd_count}</p>
              <p className="text-xs text-blue-600 mt-1">JDs Analyzed</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-purple-700">{analysis.total_unique_skills}</p>
              <p className="text-xs text-purple-600 mt-1">Unique Skills Found</p>
            </div>
            <div className="bg-orange-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-orange-700">{analysis.missing_from_profile.length}</p>
              <p className="text-xs text-orange-600 mt-1">Profile Gaps</p>
            </div>
          </div>

          <div className="flex gap-2">
            {tabBtn("overview", "Top Skills")}
            {tabBtn("breakdown", "By Category")}
            {analysis.profile_provided && tabBtn("gaps", `Gaps (${analysis.missing_from_profile.length})`)}
          </div>

          <Card>
            <CardContent className="pt-4">
              {activeTab === "overview" && (
                <div className="space-y-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" /> Most Requested Skills
                  </h3>
                  <div className="space-y-2">
                    {analysis.top_skills.map(s => (
                      <SkillBar key={s.skill} entry={s} maxCount={Math.max(...analysis.top_skills.map(x => x.count), 1)} />
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "breakdown" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <SkillSection title="Programming Languages" skills={analysis.top_languages} color="blue" />
                  <SkillSection title="Frameworks & Libraries" skills={analysis.top_frameworks} color="purple" />
                  <SkillSection title="Tools & DevOps" skills={analysis.top_tools} color="green" />
                  <SkillSection title="Cloud Platforms" skills={analysis.top_cloud} color="orange" />
                  <SkillSection title="Databases" skills={analysis.top_databases} color="teal" />
                  <SkillSection title="Concepts & Practices" skills={analysis.top_concepts} color="red" />
                </div>
              )}

              {activeTab === "gaps" && analysis.profile_provided && (
                <div className="space-y-3">
                  <h3 className="font-semibold flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" /> Missing From Your Profile
                  </h3>
                  {analysis.missing_from_profile.length === 0 ? (
                    <p className="text-sm text-green-600 font-medium">Great! Your profile covers the top market skills.</p>
                  ) : (
                    <div className="space-y-2">
                      {analysis.missing_from_profile.map(s => (
                        <div key={s.skill} className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg">
                          <div>
                            <span className="font-medium text-sm">{s.skill}</span>
                            <Badge variant="outline" className="ml-2 text-xs">{s.category}</Badge>
                          </div>
                          <div className="text-right">
                            <span className="text-sm font-bold text-orange-700">{s.percentage}%</span>
                            <p className="text-xs text-muted-foreground">of {analysis.jd_count} JDs</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
