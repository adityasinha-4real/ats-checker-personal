"use client";
import { useEffect, useState } from "react";
import { resumeApi, jdApi, type Resume, type JobDescriptionListItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/use-toast";
import { Trash2, FileText, Briefcase, RefreshCw, Info } from "lucide-react";
import { formatDate } from "@/lib/utils";

export default function SettingsPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jds, setJds] = useState<JobDescriptionListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const [r, j] = await Promise.all([resumeApi.list(), jdApi.list()]);
    setResumes(r);
    setJds(j);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const deleteResume = async (id: number) => {
    try {
      await resumeApi.delete(id);
      setResumes((p) => p.filter((r) => r.id !== id));
      toast({ title: "Resume deleted" });
    } catch {
      toast({ title: "Failed to delete resume", variant: "destructive" });
    }
  };

  const deleteJd = async (id: number) => {
    try {
      await jdApi.delete(id);
      setJds((p) => p.filter((j) => j.id !== id));
      toast({ title: "Job description deleted" });
    } catch {
      toast({ title: "Failed to delete JD", variant: "destructive" });
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your data and application settings</p>
      </div>

      {/* App Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4" /> Application Info
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div><dt className="text-muted-foreground">Version</dt><dd className="font-medium">1.0.0</dd></div>
            <div><dt className="text-muted-foreground">Backend</dt><dd className="font-medium">FastAPI + Python 3.12</dd></div>
            <div><dt className="text-muted-foreground">NLP</dt><dd className="font-medium">spaCy + MiniLM</dd></div>
            <div><dt className="text-muted-foreground">Database</dt><dd className="font-medium">SQLite (local)</dd></div>
            <div><dt className="text-muted-foreground">Frontend</dt><dd className="font-medium">Next.js 15 + Shadcn UI</dd></div>
            <div><dt className="text-muted-foreground">Cloud</dt><dd className="font-medium text-green-600">None (100% local)</dd></div>
          </dl>
        </CardContent>
      </Card>

      {/* Scoring Weights Info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Scoring Weights</CardTitle>
          <CardDescription>How the overall ATS score is calculated</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { label: "Keyword Match", weight: "35%", desc: "Exact + fuzzy match of JD keywords in resume" },
              { label: "Skills Match", weight: "25%", desc: "Technical skills extracted from JD vs resume" },
              { label: "Experience Match", weight: "15%", desc: "Years of experience comparison" },
              { label: "Education Match", weight: "10%", desc: "Degree level comparison" },
              { label: "Semantic Similarity", weight: "15%", desc: "Deep NLP sentence embedding similarity (MiniLM)" },
            ].map(({ label, weight, desc }) => (
              <div key={label} className="flex items-center gap-4">
                <div className="w-32 shrink-0">
                  <span className="text-sm font-medium">{label}</span>
                </div>
                <div className="w-12 shrink-0">
                  <span className="text-sm font-bold text-blue-600">{weight}</span>
                </div>
                <span className="text-sm text-muted-foreground">{desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Manage Resumes */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4" /> Uploaded Resumes ({resumes.length})
            </CardTitle>
            <CardDescription>Delete resumes you no longer need</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw className="h-4 w-4" /></Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : resumes.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No resumes uploaded</p>
          ) : (
            <div className="space-y-2">
              {resumes.map((r) => (
                <div key={r.id} className="flex items-center gap-3 p-3 rounded border hover:bg-muted/20">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{r.original_filename}</p>
                    <p className="text-xs text-muted-foreground">{r.file_type.toUpperCase()} · {formatDate(r.created_at)}</p>
                  </div>
                  <button onClick={() => deleteResume(r.id)} className="text-gray-400 hover:text-red-500 p-1" title="Delete">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Manage JDs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Briefcase className="h-4 w-4" /> Saved Job Descriptions ({jds.length})
          </CardTitle>
          <CardDescription>Delete job descriptions you no longer need</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : jds.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No saved job descriptions</p>
          ) : (
            <div className="space-y-2">
              {jds.map((jd) => (
                <div key={jd.id} className="flex items-center gap-3 p-3 rounded border hover:bg-muted/20">
                  <Briefcase className="h-4 w-4 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{jd.title}</p>
                    <p className="text-xs text-muted-foreground">{jd.company || "No company"} · {formatDate(jd.created_at)}</p>
                  </div>
                  <button onClick={() => deleteJd(jd.id)} className="text-gray-400 hover:text-red-500 p-1" title="Delete">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
