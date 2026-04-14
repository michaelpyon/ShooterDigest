"use client";

import { useState, useEffect, useCallback } from "react";
import { Sparkline } from "@/components/sparkline";
import { ScoreBadge } from "@/components/score-badge";

interface TitleOption {
  id: number;
  name: string;
  slug: string;
  genre: string;
  hasSteamData: boolean;
  compositeScore: number;
}

interface CompareData {
  name: string;
  slug: string;
  hasSteamData: boolean;
  data: Array<{
    weekOf: string;
    compositeScore: number;
    playerCountAvg: number | null;
    redditVolumeAvg: number | null;
    newsCountAvg: number | null;
  }>;
}

const CHART_COLORS = [
  "#adc6ff",
  "#4ae176",
  "#f59e0b",
  "#ffb3ad",
  "#a855f7",
  "#06b6d4",
];

export default function ComparePage() {
  const [titles, setTitles] = useState<TitleOption[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<CompareData[]>([]);
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(false);

  // Load available titles
  useEffect(() => {
    fetch("/api/titles")
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setTitles(data);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch comparison data when selection changes
  const fetchComparison = useCallback(async () => {
    if (selected.length < 2) {
      setCompareData([]);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(
        `/api/scores?slugs=${selected.join(",")}&days=${days}`
      );
      const data = await res.json();
      if (Array.isArray(data)) {
        setCompareData(data);
      }
    } catch {
      // network error
    } finally {
      setLoading(false);
    }
  }, [selected, days]);

  useEffect(() => {
    fetchComparison();
  }, [fetchComparison]);

  function toggleTitle(slug: string) {
    setSelected((prev) =>
      prev.includes(slug)
        ? prev.filter((s) => s !== slug)
        : prev.length < 6
          ? [...prev, slug]
          : prev
    );
  }

  // Build unified timeline from all selected titles
  const allWeeks = Array.from(
    new Set(compareData.flatMap((d) => d.data.map((p) => p.weekOf)))
  ).sort();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-black text-text tracking-tight">
          Compare Titles
        </h1>
        <p className="text-text-subtle text-sm mt-1">
          Select 2-6 titles to overlay their health score trends.
        </p>
      </div>

      {/* Title selection */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-text-muted text-xs uppercase tracking-widest font-medium">
            Select titles ({selected.length}/6)
          </span>
          <div className="flex items-center gap-2">
            <span className="text-text-subtle text-xs">Period:</span>
            {[30, 90, 180].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`text-xs px-3 py-1 min-h-[44px] transition-colors ${
                  days === d
                    ? "bg-accent text-bg"
                    : "text-text-subtle hover:text-text-muted bg-surface"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {titles.map((t) => {
            const isSelected = selected.includes(t.slug);
            const colorIdx = selected.indexOf(t.slug);
            return (
              <button
                key={t.slug}
                onClick={() => toggleTitle(t.slug)}
                className={`text-xs px-3 py-1.5 min-h-[44px] border transition-colors duration-150 ${
                  isSelected
                    ? "border-accent bg-accent/10 text-text"
                    : "border-border bg-surface text-text-muted hover:border-border-hover hover:text-text"
                }`}
              >
                {isSelected && (
                  <span
                    className="inline-block w-2 h-2 rounded-full mr-1.5"
                    style={{
                      backgroundColor: CHART_COLORS[colorIdx] ?? "#adc6ff",
                    }}
                  />
                )}
                {t.name}
                {!t.hasSteamData && (
                  <span className="text-warning ml-1">*</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Comparison chart */}
      {selected.length < 2 && (
        <div className="text-center py-16 border border-border bg-surface">
          <p className="text-text-subtle text-sm">
            Select at least 2 titles to compare.
          </p>
        </div>
      )}

      {loading && selected.length >= 2 && (
        <div className="text-center py-16 border border-border bg-surface">
          <p className="text-text-subtle text-sm">Loading comparison data...</p>
        </div>
      )}

      {!loading && compareData.length >= 2 && (
        <div className="space-y-6">
          {/* Overlay chart using SVG */}
          <div className="bg-surface border border-border p-6">
            <h2 className="text-text font-semibold text-sm mb-4">
              Health Score Trends
            </h2>
            {allWeeks.length >= 2 ? (
              <ComparisonChart
                data={compareData}
                weeks={allWeeks}
                colors={CHART_COLORS}
              />
            ) : (
              <p className="text-text-subtle text-sm text-center py-8">
                Not enough historical data for comparison yet. Data builds over
                weekly pipeline runs.
              </p>
            )}
          </div>

          {/* Side-by-side stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {compareData.map((title, i) => {
              const latest = title.data[title.data.length - 1];
              const sparkData = title.data.map((d) => d.compositeScore);
              return (
                <div
                  key={title.slug}
                  className="bg-surface border border-border p-4"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{
                        backgroundColor: CHART_COLORS[i] ?? "#adc6ff",
                      }}
                    />
                    <h3 className="text-text font-semibold text-sm truncate">
                      {title.name}
                    </h3>
                    {!title.hasSteamData && (
                      <span className="text-[10px] font-medium text-warning bg-warning/10 px-1.5 py-0.5 shrink-0">
                        Limited
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <ScoreBadge
                      score={latest?.compositeScore ?? 0}
                      size="sm"
                    />
                    {sparkData.length >= 2 && (
                      <Sparkline
                        data={sparkData}
                        width={64}
                        height={20}
                        color={CHART_COLORS[i]}
                      />
                    )}
                  </div>
                  {latest && (
                    <div className="mt-2 text-text-subtle text-xs space-y-0.5">
                      {latest.playerCountAvg != null && (
                        <p>
                          Players: {latest.playerCountAvg.toLocaleString()}
                        </p>
                      )}
                      {latest.redditVolumeAvg != null && (
                        <p>Reddit posts: {latest.redditVolumeAvg}</p>
                      )}
                      {latest.newsCountAvg != null && (
                        <p>News articles: {latest.newsCountAvg}</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Legend footnote */}
      <p className="text-text-subtle text-xs mt-6">
        * Limited Data: title lacks Steam player count. Score uses Reddit (60%)
        + News (40%) only.
      </p>
    </div>
  );
}

/**
 * SVG-based multi-line comparison chart.
 */
function ComparisonChart({
  data,
  weeks,
  colors,
}: {
  data: CompareData[];
  weeks: string[];
  colors: string[];
}) {
  const width = 680;
  const height = 200;
  const padding = { top: 10, right: 10, bottom: 30, left: 40 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Find min/max across all data
  const allScores = data.flatMap((d) => d.data.map((p) => p.compositeScore));
  const minScore = Math.max(0, Math.min(...allScores) - 5);
  const maxScore = Math.min(100, Math.max(...allScores) + 5);
  const scoreRange = maxScore - minScore || 1;

  function xPos(weekStr: string): number {
    const idx = weeks.indexOf(weekStr);
    return padding.left + (idx / Math.max(weeks.length - 1, 1)) * chartWidth;
  }

  function yPos(score: number): number {
    return (
      padding.top + (1 - (score - minScore) / scoreRange) * chartHeight
    );
  }

  // Y-axis labels
  const yLabels = [minScore, (minScore + maxScore) / 2, maxScore].map(
    Math.round
  );

  // X-axis labels (show first, middle, last)
  const xLabels =
    weeks.length >= 3
      ? [weeks[0], weeks[Math.floor(weeks.length / 2)], weeks[weeks.length - 1]]
      : weeks;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Grid lines */}
      {yLabels.map((val) => (
        <g key={val}>
          <line
            x1={padding.left}
            y1={yPos(val)}
            x2={width - padding.right}
            y2={yPos(val)}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="0.5"
          />
          <text
            x={padding.left - 6}
            y={yPos(val) + 3}
            fill="#8c909f"
            fontSize="9"
            textAnchor="end"
            fontFamily="monospace"
          >
            {val}
          </text>
        </g>
      ))}

      {/* X-axis labels */}
      {xLabels.map((week) => (
        <text
          key={week}
          x={xPos(week)}
          y={height - 5}
          fill="#8c909f"
          fontSize="9"
          textAnchor="middle"
          fontFamily="monospace"
        >
          {week.slice(5, 10)}
        </text>
      ))}

      {/* Data lines */}
      {data.map((series, i) => {
        if (series.data.length < 2) return null;
        const points = series.data
          .map((d) => `${xPos(d.weekOf)},${yPos(d.compositeScore)}`)
          .join(" ");
        return (
          <polyline
            key={series.slug}
            points={points}
            fill="none"
            stroke={colors[i] ?? "#adc6ff"}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );
      })}

      {/* End dots */}
      {data.map((series, i) => {
        const last = series.data[series.data.length - 1];
        if (!last) return null;
        return (
          <circle
            key={`dot-${series.slug}`}
            cx={xPos(last.weekOf)}
            cy={yPos(last.compositeScore)}
            r="3"
            fill={colors[i] ?? "#adc6ff"}
          />
        );
      })}
    </svg>
  );
}
