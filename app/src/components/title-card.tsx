import Link from "next/link";
import { ScoreBadge, ChangeIndicator } from "./score-badge";
import { Sparkline } from "./sparkline";
import { formatNumber } from "@/lib/utils";

export interface TitleCardData {
  rank: number;
  name: string;
  slug: string;
  genre: string;
  compositeScore: number;
  change: number | null;
  currentPlayers: number | null;
  hasSteamData: boolean;
  sparklineData: number[];
  sentimentScore: number | null;
}

interface TitleCardProps {
  data: TitleCardData;
}

export function TitleCard({ data }: TitleCardProps) {
  return (
    <Link
      href={`/title/${data.slug}`}
      className="block bg-[#111111] border border-[#1f2937] rounded-lg p-4 hover:bg-[#1a1a1a] hover:border-[#334155] transition-all"
    >
      <div className="flex items-start justify-between gap-4">
        {/* Left: rank + info */}
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <span className="mono text-[#6b7280] text-sm font-medium w-6 text-right shrink-0 pt-0.5">
            {data.rank}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-[#e2e8f0] font-semibold text-sm truncate">
                {data.name}
              </h3>
              {!data.hasSteamData && (
                <span className="text-[10px] font-medium text-[#f59e0b] bg-[#f59e0b]/10 px-1.5 py-0.5 rounded shrink-0">
                  Limited Data
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[#6b7280] text-xs">{data.genre}</span>
              {data.currentPlayers != null && (
                <span className="mono text-[#94a3b8] text-xs">
                  {formatNumber(data.currentPlayers)} players
                </span>
              )}
              {data.sentimentScore != null && (
                <span
                  className={`text-xs ${
                    data.sentimentScore >= 0.05
                      ? "text-[#22c55e]"
                      : data.sentimentScore <= -0.05
                        ? "text-[#ef4444]"
                        : "text-[#6b7280]"
                  }`}
                >
                  {data.sentimentScore >= 0.05
                    ? "Positive"
                    : data.sentimentScore <= -0.05
                      ? "Negative"
                      : "Neutral"}{" "}
                  sentiment
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right: score + sparkline */}
        <div className="flex items-center gap-4 shrink-0">
          {data.sparklineData.length >= 2 && (
            <Sparkline data={data.sparklineData} width={72} height={24} />
          )}
          <div className="text-right">
            <ScoreBadge score={data.compositeScore} size="sm" />
            <div className="mt-1">
              <ChangeIndicator change={data.change} />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
