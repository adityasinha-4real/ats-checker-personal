"use client";
import { useEffect, useState } from "react";
import { analysisApi, type DashboardStats, type AnalysisListItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatScore, getScoreColor, getScoreBg, formatDate } from "@/lib/utils";
import { FileText, Briefcase, BarChart3, TrendingUp, AlertCircle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import Link from "next/link";

function StatCard({ title, value, icon: Icon, sub }: { title: string; value: string | number; icon: React.ElementType; sub?: string }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </div>
          <div className="p-2.5 rounded-lg bg-blue-50">
            <Icon className="h-5 w-5 text-blue-600" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getBarColor(score: number) {
  if (score >= 75) return "#059669";
  if (score >= 50) return "#d97706";
  return "#dc2626";
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analysisApi.dashboard()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
        <p className="text-lg font-medium text-gray-700">Cannot connect to backend</p>
        <p className="text-sm text-muted-foreground mt-1">Make sure the FastAPI server is running on port 8000</p>
        <code className="mt-3 px-3 py-1 bg-gray-100 rounded text-sm text-gray-600">cd backend && python -m uvicorn app.main:app --reload</code>
      </div>
    );
  }

  const chartData = stats?.recent_analyses?.map((a) => ({
    name: a.resume?.original_filename?.replace(/\.[^.]+$/, "").slice(0, 12) || `#${a.id}`,
    score: a.overall_score,
  })) ?? [];

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your ATS analyses</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Resumes Uploaded" value={stats?.total_resumes ?? 0} icon={FileText} />
        <StatCard title="Job Descriptions" value={stats?.total_jds ?? 0} icon={Briefcase} />
        <StatCard title="Analyses Run" value={stats?.total_analyses ?? 0} icon={BarChart3} />
        <StatCard
          title="Average ATS Score"
          value={stats?.avg_score ? `${stats.avg_score.toFixed(1)}` : "–"}
          icon={TrendingUp}
          sub={stats?.top_score ? `Top: ${stats.top_score.toFixed(1)}` : undefined}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Analysis Scores</CardTitle>
            <CardDescription>Last {chartData.length} analyses</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <BarChart3 className="h-8 w-8 text-gray-300 mb-2" />
                <p className="text-sm text-muted-foreground">No analyses yet</p>
                <Link href="/analysis" className="mt-2 text-sm text-blue-600 hover:underline">Run your first analysis →</Link>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => [`${v.toFixed(1)}`, "ATS Score"]} />
                  <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={getBarColor(entry.score)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Analyses</CardTitle>
          </CardHeader>
          <CardContent>
            {(stats?.recent_analyses ?? []).length === 0 ? (
              <div className="text-center py-12">
                <p className="text-sm text-muted-foreground">No analyses yet.</p>
                <Link href="/analysis" className="mt-2 text-sm text-blue-600 hover:underline block">Start analysing resumes →</Link>
              </div>
            ) : (
              <div className="space-y-3">
                {stats!.recent_analyses.map((a) => (
                  <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/30 transition-colors">
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{a.resume?.original_filename || "Unknown"}</p>
                      <p className="text-xs text-muted-foreground truncate">{a.job_description?.title || "N/A"} · {formatDate(a.created_at)}</p>
                    </div>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold shrink-0 ${getScoreBg(a.overall_score)}`}>
                      {formatScore(a.overall_score)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {stats?.total_analyses === 0 && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="p-6 text-center">
            <h3 className="font-semibold text-blue-900 mb-2">Get Started</h3>
            <p className="text-sm text-blue-700 mb-4">Upload a resume and paste a job description to run your first ATS analysis.</p>
            <Link href="/analysis" className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors">
              Run First Analysis →
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
