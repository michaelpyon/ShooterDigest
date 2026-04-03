/**
 * Health score badge with color coding.
 * 80-100: Green (thriving)
 * 60-79: Blue (healthy)
 * 40-59: Amber (neutral)
 * 20-39: Orange (declining)
 * 0-19: Red (critical)
 */

interface ScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-secondary";
  if (score >= 60) return "text-accent";
  if (score >= 40) return "text-warning";
  if (score >= 20) return "text-[#f97316]";
  return "text-tertiary";
}

function getScoreBg(score: number): string {
  if (score >= 80) return "bg-secondary/10";
  if (score >= 60) return "bg-accent/10";
  if (score >= 40) return "bg-warning/10";
  if (score >= 20) return "bg-[#f97316]/10";
  return "bg-tertiary/10";
}

const sizes = {
  sm: "text-sm px-2 py-0.5",
  md: "text-lg px-3 py-1",
  lg: "text-2xl px-4 py-2",
};

export function ScoreBadge({
  score,
  size = "md",
  className = "",
}: ScoreBadgeProps) {
  return (
    <span
      className={`mono font-bold ${getScoreColor(score)} ${getScoreBg(score)} ${sizes[size]} ${className}`}
    >
      {score.toFixed(1)}
    </span>
  );
}

export function ChangeIndicator({
  change,
  className = "",
}: {
  change: number | null;
  className?: string;
}) {
  if (change == null) {
    return (
      <span className={`mono text-text-subtle text-xs ${className}`}>--</span>
    );
  }

  const isPositive = change >= 0;
  const color = isPositive ? "text-secondary" : "text-tertiary";
  const arrow = isPositive ? "\u25B2" : "\u25BC";
  const sign = isPositive ? "+" : "";

  return (
    <span className={`mono text-xs ${color} ${className}`}>
      {arrow} {sign}
      {change.toFixed(1)}
    </span>
  );
}
