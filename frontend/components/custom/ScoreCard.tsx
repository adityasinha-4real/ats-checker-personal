"use client";
import { cn, formatScore, getScoreColor, getProgressColor } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

interface ScoreCardProps {
  label: string;
  score: number;
  weight?: string;
  description?: string;
  className?: string;
}

export function ScoreCard({ label, score, weight, description, className }: ScoreCardProps) {
  return (
    <Card className={cn("", className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{label}</p>
            {weight && <p className="text-xs text-muted-foreground/60">Weight: {weight}</p>}
          </div>
          <span className={cn("text-2xl font-bold", getScoreColor(score))}>
            {formatScore(score)}
          </span>
        </div>
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className={cn("h-full rounded-full transition-all duration-500", getProgressColor(score))}
            style={{ width: `${Math.min(100, score)}%` }}
          />
        </div>
        {description && <p className="text-xs text-muted-foreground mt-2">{description}</p>}
      </CardContent>
    </Card>
  );
}

interface OverallScoreProps {
  score: number;
  className?: string;
}

export function OverallScore({ score, className }: OverallScoreProps) {
  const color = score >= 75 ? "#059669" : score >= 50 ? "#d97706" : "#dc2626";
  const label = score >= 75 ? "Excellent" : score >= 60 ? "Good" : score >= 45 ? "Fair" : "Needs Work";

  return (
    <div className={cn("flex flex-col items-center justify-center", className)}>
      <div className="relative w-40 h-40">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="10" />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={`${2 * Math.PI * 40}`}
            strokeDashoffset={`${2 * Math.PI * 40 * (1 - score / 100)}`}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold" style={{ color }}>
            {score.toFixed(0)}
          </span>
          <span className="text-xs text-muted-foreground">/100</span>
        </div>
      </div>
      <span className="mt-2 text-sm font-semibold" style={{ color }}>{label}</span>
    </div>
  );
}
