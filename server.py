"""Tiny server that serves the latest Shooter Digest HTML."""

import os
import re
import glob
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
NEIGHBORHOODS_FILE = os.path.join(BASE_DIR, "nyc-neighborhoods.html")
NYCGUY_FILE = os.path.join(BASE_DIR, "nycguy.html")


class DigestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def end_headers(self):
        # Prevent aggressive caching so new deploys are seen immediately
        self.send_header("Cache-Control", "no-cache, max-age=0")
        super().end_headers()

    def do_GET(self):
        # Health check
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Digest archive index
        if self.path in ("/digests", "/digests/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self._build_index_page().encode("utf-8"))
            return

        # Serve the NYC guy diagnostic
        if self.path in ("/nyc", "/nyc/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(NYCGUY_FILE, "rb") as f:
                self.wfile.write(f.read())
            return

        # Serve the NYC neighborhood ranker
        if self.path in ("/neighborhoods", "/neighborhoods/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(NEIGHBORHOODS_FILE, "rb") as f:
                self.wfile.write(f.read())
            return

        # Serve the latest digest HTML at /
        if self.path == "/" or self.path == "/index.html":
            files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html")))
            if files:
                self.path = "/" + os.path.basename(files[-1])
        super().do_GET()

    def _build_index_page(self) -> str:
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html")), reverse=True)
        if not files:
            return "<html><body><h1>No digests yet.</h1></body></html>"

        # Stats bar values
        digest_count = len(files)
        earliest_name = os.path.basename(files[-1])  # files sorted newest-first
        earliest_date_str = earliest_name.replace("digest_", "").replace(".html", "")
        try:
            since_str = datetime.strptime(earliest_date_str, "%Y-%m-%d").strftime("%B %Y")
        except ValueError:
            since_str = earliest_date_str

        # Build digest cards
        cards = []
        for f in files:
            name = os.path.basename(f)
            date_str = name.replace("digest_", "").replace(".html", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = dt.strftime("Week of %B %-d, %Y")
            except ValueError:
                formatted_date = date_str

            teaser = self._extract_teaser(f)
            cards.append(f"""
  <div class="digest-card">
    <div class="digest-date">{formatted_date}</div>
    <div class="digest-teaser">{teaser}</div>
    <a class="digest-link" href="/{name}">→ Read digest</a>
  </div>""")

        items = "\n".join(cards)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Weekly FPS intelligence digest — Steam concurrents, Reddit sentiment, press coverage">
<title>ShooterDigest — Archive</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0f1923; color: #c7d5e0; max-width: 640px; margin: 60px auto; padding: 0 20px; }}
  .about-section {{ padding-bottom: 2rem; margin-bottom: 2rem; border-bottom: 1px solid #2a475e; }}
  .about-title {{ color: #66c0f4; font-size: 2rem; font-weight: 700; margin-bottom: 0.4rem; }}
  .about-subtitle {{ color: #8f98a0; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0.75rem; }}
  .stats-bar {{ color: #4a5568; font-size: 0.78rem; letter-spacing: 0.01em; }}
  .digests-section h2 {{ color: #8f98a0; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; }}
  .digest-card {{ padding: 1rem 0; border-bottom: 1px solid #1b2838; }}
  .digest-card:last-child {{ border-bottom: none; }}
  .digest-date {{ color: #c7d5e0; font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }}
  .digest-teaser {{ color: #6b7280; font-size: 0.82rem; line-height: 1.5; margin-bottom: 0.4rem; }}
  .digest-link {{ color: #66c0f4; font-size: 0.85rem; text-decoration: none; }}
  .digest-link:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="about-section">
  <div class="about-title">ShooterDigest</div>
  <div class="about-subtitle">Weekly intelligence on the live FPS landscape. Steam player counts, Reddit sentiment, and press coverage — synthesized every Monday.</div>
  <div class="stats-bar">{digest_count} digests published &middot; Tracking 16 games &middot; Since {since_str}</div>
</div>
<div class="digests-section">
  <h2>Archive</h2>
  {items}
</div>
</body>
</html>"""

    def _extract_teaser(self, filepath: str) -> str:
        """Pull the first <li> text from a digest file as a one-line teaser."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                content = fh.read(40000)
            match = re.search(r"<li>(.*?)</li>", content, re.DOTALL)
            if match:
                text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                return (text[:100] + "…") if len(text) > 100 else text
        except Exception:
            pass
        return "Weekly FPS intelligence digest"


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DigestHandler)
    print(f"Serving Shooter Digest on port {PORT}")
    print(f"  /              → latest digest")
    print(f"  /neighborhoods → NYC neighborhood ranker")
    print(f"  /nyc           → The Jawnz Diagnostic")
    server.serve_forever()
