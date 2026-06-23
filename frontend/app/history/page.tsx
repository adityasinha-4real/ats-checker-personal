"use client";
import { useEffect, useState } from "react";
import { analysisApi, type AnalysisListItem, exportApi } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatScore, getScoreBg, formatDate } from "@/lib/utils";
import { FileText, Download, Trash2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/use-toast";

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    analysisApi.list(0, 100)
      .then(setAnalyses)
      .catch(() => toast({ title: "Failed to load history", variant: "destructive" }))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number) => {
    try {
      await analysisApi.delete(id);
      setAnalyses((prev) => prev.filter((a) => a.id !== id));
      toast({ title: "Deleted", description: "Analysis removed from history." });
    } catch {
      toast({ title: "Delete failed", variant: "destructive" });
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">History</h1>
          <p className="text-muted-foreground mt-1">All previous ATS analyses</p>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="h-4 w-4 mr-2" /> Refresh
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : analyses.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText className="h-10 w-10 text-gray-300 mx-auto mb-3" />
            <p className="text-muted-foreground">No analyses yet. Run your first analysis to see it here.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {analyses.map((a) => (
            <Card key={a.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <FileText className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-sm truncate max-w-xs">
                        {a.resume?.original_filename || "Unknown Resume"}
                      </p>
                      <span className="text-muted-foreground text-sm">vs</span>
                      <p className="text-sm text-blue-700 font-medium truncate max-w-xs">
                        {a.job_description?.title || "N/A"}
                        {a.job_description?.company ? ` @ ${a.job_description.company}` : ""}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{formatDate(a.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getScoreBg(a.overall_score)}`}>
                      {formatScore(a.overall_score)}
                    </span>
                    <a
                      href={exportApi.pdf(a.id)}
                      download
                      className="p-1.5 text-gray-400 hover:text-gray-600 rounded"
                      title="Download PDF"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="p-1.5 text-gray-400 hover:text-red-500 rounded"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        {analyses.length} total {analyses.length === 1 ? "analysis" : "analyses"}
      </p>
    </div>
  );
}
