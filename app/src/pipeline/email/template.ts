/**
 * HTML email template for the weekly ShooterDigest.
 * Dark theme, responsive, matches the dashboard aesthetic.
 */

interface DigestTitle {
  name: string;
  slug: string;
  compositeScore: number;
  previousScore: number | null;
  change: number | null;
  hasSteamData: boolean;
}

interface DigestData {
  titles: DigestTitle[];
  topMovers: DigestTitle[];
  biggestDrops: DigestTitle[];
  weekOf: string;
}

export function buildDigestHtml(
  data: DigestData,
  siteUrl: string
): { subject: string; html: string } {
  const topMover = data.topMovers[0];
  const topDrop = data.biggestDrops[0];

  const subject = topMover && topDrop
    ? `ShooterDigest: ${topMover.name} up ${(topMover.change ?? 0).toFixed(1)}%, ${topDrop.name} down ${Math.abs(topDrop.change ?? 0).toFixed(1)}%`
    : `ShooterDigest: Weekly FPS Intelligence (${data.weekOf})`;

  const titleRows = data.titles
    .map((t, i) => {
      const changeStr =
        t.change != null
          ? t.change >= 0
            ? `<span style="color:#22c55e">+${t.change.toFixed(1)}</span>`
            : `<span style="color:#ef4444">${t.change.toFixed(1)}</span>`
          : `<span style="color:#6b7280">--</span>`;

      const badge = !t.hasSteamData
        ? ' <span style="color:#f59e0b;font-size:11px;">[Limited]</span>'
        : "";

      return `
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:8px 12px;color:#94a3b8;font-size:13px;">${i + 1}</td>
          <td style="padding:8px 12px;">
            <a href="${siteUrl}/title/${t.slug}" style="color:#e2e8f0;text-decoration:none;font-weight:500;">${t.name}</a>${badge}
          </td>
          <td style="padding:8px 12px;text-align:right;font-family:monospace;color:#e2e8f0;font-size:15px;font-weight:600;">${t.compositeScore.toFixed(1)}</td>
          <td style="padding:8px 12px;text-align:right;font-family:monospace;font-size:13px;">${changeStr}</td>
        </tr>`;
    })
    .join("");

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="padding:16px 0;border-bottom:1px solid #1e293b;margin-bottom:24px;">
      <h1 style="margin:0;color:#e2e8f0;font-size:20px;font-weight:700;letter-spacing:-0.5px;">ShooterDigest</h1>
      <p style="margin:4px 0 0;color:#64748b;font-size:13px;">Week of ${data.weekOf}</p>
    </div>

    <!-- League Table -->
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <thead>
        <tr style="border-bottom:2px solid #1e293b;">
          <th style="padding:8px 12px;text-align:left;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;">#</th>
          <th style="padding:8px 12px;text-align:left;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Title</th>
          <th style="padding:8px 12px;text-align:right;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Score</th>
          <th style="padding:8px 12px;text-align:right;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;">WoW</th>
        </tr>
      </thead>
      <tbody>
        ${titleRows}
      </tbody>
    </table>

    <!-- CTA -->
    <div style="text-align:center;padding:16px 0;margin-bottom:24px;">
      <a href="${siteUrl}" style="display:inline-block;padding:10px 24px;background:#3b82f6;color:#ffffff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:500;">Explore the full dashboard</a>
    </div>

    <!-- Footer -->
    <div style="border-top:1px solid #1e293b;padding-top:16px;text-align:center;">
      <p style="color:#64748b;font-size:11px;margin:0;">
        ShooterDigest: Competitive FPS market intelligence.
      </p>
      <p style="margin:8px 0 0;">
        <a href="{{UNSUBSCRIBE_URL}}" style="color:#64748b;font-size:11px;text-decoration:underline;">Unsubscribe</a>
      </p>
    </div>

  </div>
</body>
</html>`;

  return { subject, html };
}
