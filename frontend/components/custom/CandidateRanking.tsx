"use client";
import { useState } from "react";
import { RankingItem } from "@/lib/api";
import { formatScore, getScoreBg, formatDate, getRankBadgeColor } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Download, Eye } from "lucide-react";
import { exportApi } from "@/lib/api";

interface Props {
  rankings: RankingItem[];
  jdId: number;
  onViewAnalysis?: (analysisId: number) => void;
}

type SortKey = "rank" | "keyword_score" | "skills_score" | "semantic_score";

export function CandidateRanking({ rankings, jdId, onViewAnalysis }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("rank");
  const [sortAsc, setSortAsc] = useState(true);

  const sorted = [...rankings].sort((a, b) => {
    let av: number, bv: number;
    if (sortKey === "rank") { av = a.rank; bv = b.rank; }
    else {
      av = a.analysis?.[sortKey] ?? 0;
      bv = b.analysis?.[sortKey] ?? 0;
    }
    return sortAsc ? av - bv : bv - av;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(key === "rank"); }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />) : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Candidate Ranking ({rankings.length})</CardTitle>
        <a
          href={exportApi.csv(jdId)}
          download
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border bg-background hover:bg-accent transition-colors"
        >
          <Download className="h-4 w-4" /> Export CSV
        </a>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 font-medium cursor-pointer" onClick={() => toggleSort("rank")}>
                  <span className="flex items-center gap-1">Rank <SortIcon k="rank" /></span>
                </th>
                <th className="text-left p-3 font-medium">Candidate</th>
                <th className="text-right p-3 font-medium">Overall</th>
                <th className="text-right p-3 font-medium cursor-pointer" onClick={() => toggleSort("keyword_score")}>
                  <span className="flex items-center justify-end gap-1">Keywords <SortIcon k="keyword_score" /></span>
                </th>
                <th className="text-right p-3 font-medium cursor-pointer" onClick={() => toggleSort("skills_score")}>
                  <span className="flex items-center justify-end gap-1">Skills <SortIcon k="skills_score" /></span>
                </th>
                <th className="text-right p-3 font-medium cursor-pointer" onClick={() => toggleSort("semantic_score")}>
                  <span className="flex items-center justify-end gap-1">Semantic <SortIcon k="semantic_score" /></span>
                </th>
                <th className="text-center p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((item) => {
                const name = item.resume?.parsed_data?.name || item.resume?.original_filename || "Unknown";
                return (
                  <tr key={item.id} className="border-b hover:bg-muted/30 transition-colors">
                    <td className="p-3">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full border text-xs font-bold ${getRankBadgeColor(item.rank)}`}>
                        {item.rank}
                      </span>
                    </td>
                    <td className="p-3">
                      <div>
                        <p className="font-medium">{name}</p>
                        <p className="text-xs text-muted-foreground">{item.resume?.original_filename}</p>
                      </div>
                    </td>
                    <td className="p-3 text-right">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getScoreBg(item.overall_score)}`}>
                        {formatScore(item.overall_score)}
                      </span>
                    </td>
                    <td className="p-3 text-right text-muted-foreground">
                      {item.analysis ? formatScore(item.analysis.keyword_score) : "–"}
                    </td>
                    <td className="p-3 text-right text-muted-foreground">
                      {item.analysis ? formatScore(item.analysis.skills_score) : "–"}
                    </td>
                    <td className="p-3 text-right text-muted-foreground">
                      {item.analysis ? formatScore(item.analysis.semantic_score) : "–"}
                    </td>
                    <td className="p-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        {item.analysis_id && (
                          <>
                            <button
                              onClick={() => onViewAnalysis?.(item.analysis_id!)}
                              className="text-blue-600 hover:text-blue-800"
                              title="View Analysis"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            <a
                              href={exportApi.pdf(item.analysis_id)}
                              download
                              className="text-gray-500 hover:text-gray-700"
                              title="Download PDF"
                            >
                              <Download className="h-4 w-4" />
                            </a>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rankings.length === 0 && (
            <p className="text-center text-muted-foreground py-12">
              No candidates ranked yet. Run an analysis first.
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
