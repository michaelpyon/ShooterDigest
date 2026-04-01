import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShooterDigest | Competitive FPS Market Intelligence",
  description:
    "Weekly competitive FPS market intelligence. Player counts, community sentiment, and news coverage for every major shooter.",
  openGraph: {
    title: "ShooterDigest",
    description: "Competitive FPS market intelligence dashboard.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0a]">
        <nav className="border-b border-[#1f2937] bg-[#0a0a0a] sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <div className="flex items-center gap-8">
                <a
                  href="/"
                  className="text-[#e2e8f0] font-bold text-lg tracking-tight"
                >
                  ShooterDigest
                </a>
                <div className="hidden sm:flex items-center gap-6">
                  <a
                    href="/compare"
                    className="text-[#94a3b8] hover:text-[#e2e8f0] text-sm transition-colors"
                  >
                    Compare
                  </a>
                  <a
                    href="/methodology"
                    className="text-[#94a3b8] hover:text-[#e2e8f0] text-sm transition-colors"
                  >
                    Methodology
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="/api/rss"
                  className="text-[#64748b] hover:text-[#94a3b8] text-xs transition-colors"
                  title="RSS Feed"
                >
                  RSS
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
