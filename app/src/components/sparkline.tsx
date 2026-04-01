"use client";

/**
 * Sparkline chart component.
 * Pure SVG, no library dependency for the tiny inline charts.
 * Uses Recharts for the full-size charts on detail pages.
 */

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color,
  className = "",
}: SparklineProps) {
  if (data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  // Determine color from trend direction
  const trend = data[data.length - 1] - data[0];
  const lineColor = color ?? (trend >= 0 ? "#22c55e" : "#ef4444");

  const padding = 2;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1)) * chartWidth;
    const y = padding + (1 - (val - min) / range) * chartHeight;
    return `${x},${y}`;
  });

  const polyline = points.join(" ");

  // Area fill: same path but closed at bottom
  const areaPath = `M${points[0]} ${points.slice(1).map((p) => `L${p}`).join(" ")} L${padding + chartWidth},${height - padding} L${padding},${height - padding} Z`;

  return (
    <svg
      width={width}
      height={height}
      className={className}
      viewBox={`0 0 ${width} ${height}`}
    >
      <defs>
        <linearGradient
          id={`sparkGrad-${lineColor.replace("#", "")}`}
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0%" stopColor={lineColor} stopOpacity="0.2" />
          <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d={areaPath}
        fill={`url(#sparkGrad-${lineColor.replace("#", "")})`}
      />
      <polyline
        points={polyline}
        fill="none"
        stroke={lineColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
