import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

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
    <html lang="en" className={`dark ${inter.variable}`}>
      <body className="min-h-screen bg-bg font-sans">
        <nav className="border-b border-border bg-bg sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <div className="flex items-center gap-8">
                <a
                  href="/"
                  className="text-text font-bold text-lg tracking-tight"
                >
                  ShooterDigest
                </a>
                <div className="hidden sm:flex items-center gap-6">
                  <a
                    href="/compare"
                    className="text-text-muted hover:text-text text-sm transition-colors"
                  >
                    Compare
                  </a>
                  <a
                    href="/methodology"
                    className="text-text-muted hover:text-text text-sm transition-colors"
                  >
                    Methodology
                  </a>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <a
                  href="/api/rss"
                  className="text-text-subtle hover:text-text-muted text-xs transition-colors"
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
