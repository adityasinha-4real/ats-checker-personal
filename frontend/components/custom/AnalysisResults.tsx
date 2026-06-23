"use client";
import { Analysis } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScoreCard, OverallScore } from "./ScoreCard";
import { CheckCircle, XCircle, Lightbulb, TrendingUp } from "lucide-react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from "recharts";

interface Props {
  analysis: Analysis;
}

export function AnalysisResults({ analysis }: Props) {
  const radarData = [
    { subject: "Keywords", score: analysis.keyword_score, fullMark: 100 },
    { subject: "Skills", score: analysis.skills_score, fullMark: 100 },
    { subject: "Experience", score: analysis.experience_score, fullMark: 100 },
    { subject: "Education", score: analysis.education_score, fullMark: 100 },
    { subject: "Semantic", score: analysis.semantic_score, fullMark: 100 },
  ];

  return (
    <div className="space-y-6">
      {/* Overall + Radar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">ATS Score</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-center py-4">
            <OverallScore score={analysis.overall_score} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Score Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar name="Score" dataKey="score" stroke="#2563eb" fill="#2563eb" fillOpacity={0.25} />
                <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Category Scores */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ScoreCard label="Keyword Match" score={analysis.keyword_score} weight="35%" />
        <ScoreCard label="Skills Match" score={analysis.skills_score} weight="25%" />
        <ScoreCard label="Experience Match" score={analysis.experience_score} weight="15%" />
        <ScoreCard label="Education Match" score={analysis.education_score} weight="10%" />
        <ScoreCard label="Semantic Similarity" score={analysis.semantic_score} weight="15%" />
      </div>

      {/* Skills Matches */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              Matched Skills ({analysis.matched_skills.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analysis.matched_skills.length === 0 ? (
              <p className="text-sm text-muted-foreground">No skills matched</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {analysis.matched_skills.map((s) => (
                  <Badge key={s} variant="success">{s}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Missing Skills ({analysis.missing_skills.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {analysis.missing_skills.length === 0 ? (
              <p className="text-sm text-green-600 font-medium">All required skills matched!</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {analysis.missing_skills.map((s) => (
                  <Badge key={s} variant="destructive">{s}</Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Missing Keywords */}
      {analysis.missing_keywords.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-orange-500" />
              Missing Keywords
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {analysis.missing_keywords.slice(0, 20).map((kw) => (
                <Badge key={kw} variant="outline" className="text-orange-700 border-orange-300 bg-orange-50">{kw}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Suggestions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Lightbulb className="h-4 w-4 text-yellow-500" />
            Improvement Suggestions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {analysis.suggestions.length === 0 ? (
            <p className="text-sm text-green-600 font-medium">Great job! No major improvements needed.</p>
          ) : (
            <ul className="space-y-2">
              {analysis.suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0 mt-0.5">{i + 1}</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Details */}
      {analysis.details && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Analysis Details</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">Resume Words</dt>
                <dd className="font-medium">{analysis.details.resume_word_count ?? "N/A"}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Years Experience</dt>
                <dd className="font-medium">{analysis.details.resume_years_experience ?? 0}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">JD Keywords</dt>
                <dd className="font-medium">{analysis.details.jd_keywords_count ?? 0}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">JD Skills</dt>
                <dd className="font-medium">{analysis.details.jd_skills_count ?? 0}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
