"use client";
import { useEffect, useState } from "react";
import { jdApi, rankingApi, analysisApi, type JobDescriptionListItem, type RankingResponse, type Analysis } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CandidateRanking } from "@/components/custom/CandidateRanking";
import { AnalysisResults } from "@/components/custom/AnalysisResults";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function RankingPage() {
  const [jds, setJds] = useState<JobDescriptionListItem[]>([]);
  const [selectedJdId, setSelectedJdId] = useState<string>("");
  const [ranking, setRanking] = useState<RankingResponse | null>(null);
  const [loadingRanking, setLoadingRanking] = useState(false);
  const [viewingAnalysis, setViewingAnalysis] = useState<Analysis | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  useEffect(() => { jdApi.list().then(setJds); }, []);

  const handleJdChange = async (id: string) => {
    setSelectedJdId(id);
    setRanking(null);
    setViewingAnalysis(null);
    setLoadingRanking(true);
    try {
      const r = await rankingApi.get(parseInt(id));
      setRanking(r);
    } finally {
      setLoadingRanking(false);
    }
  };

  const handleViewAnalysis = async (analysisId: number) => {
    setLoadingAnalysis(true);
    try {
      const a = await analysisApi.get(analysisId);
      setViewingAnalysis(a);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Candidate Ranking</h1>
        <p className="text-muted-foreground mt-1">Compare and rank all candidates for a job description</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Select Job Description</CardTitle>
        </CardHeader>
        <CardContent>
          <Select value={selectedJdId} onValueChange={handleJdChange}>
            <SelectTrigger className="w-full max-w-md">
              <SelectValue placeholder="Choose a job description to view rankings..." />
            </SelectTrigger>
            <SelectContent>
              {jds.map((jd) => (
                <SelectItem key={jd.id} value={String(jd.id)}>
                  {jd.title} {jd.company ? `@ ${jd.company}` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {jds.length === 0 && (
            <p className="text-sm text-muted-foreground mt-2">
              No job descriptions saved yet. Go to Resume Analysis to create one.
            </p>
          )}
        </CardContent>
      </Card>

      {loadingRanking && (
        <div className="space-y-3">
          <Skeleton className="h-12" />
          <Skeleton className="h-64" />
        </div>
      )}

      {ranking && !viewingAnalysis && (
        <CandidateRanking
          rankings={ranking.rankings}
          jdId={parseInt(selectedJdId)}
          onViewAnalysis={handleViewAnalysis}
        />
      )}

      {viewingAnalysis && (
        <div>
          <Button
            variant="ghost"
            size="sm"
            className="mb-4"
            onClick={() => setViewingAnalysis(null)}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Rankings
          </Button>
          <h2 className="text-lg font-semibold mb-4">
            Analysis: {viewingAnalysis.resume?.original_filename}
          </h2>
          <AnalysisResults analysis={viewingAnalysis} />
        </div>
      )}

      {loadingAnalysis && (
        <div className="space-y-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64" />
        </div>
      )}
    </div>
  );
}
