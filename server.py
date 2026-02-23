"""Tiny server that serves the latest Shooter Digest HTML."""

import os
import glob
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

        rows = []
        for f in files:
            name = os.path.basename(f)
            # Extract date from filename like digest_2025-12-30.html
            date_str = name.replace("digest_", "").replace(".html", "")
            rows.append(
                f'<li><a href="/{name}">{date_str}</a></li>'
            )

        items = "\n".join(rows)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ShooterDigest — Archive</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0f1923; color: #c7d5e0; max-width: 600px; margin: 60px auto; padding: 0 20px; }}
  h1 {{ color: #66c0f4; margin-bottom: 8px; }}
  p {{ color: #8f98a0; margin-bottom: 24px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ margin: 8px 0; }}
  a {{ color: #66c0f4; text-decoration: none; font-size: 1.05rem; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>ShooterDigest Archive</h1>
<p>Weekly competitive FPS analytics. Pick a digest below.</p>
<ul>{items}</ul>
</body>
</html>"""


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DigestHandler)
    print(f"Serving Shooter Digest on port {PORT}")
    print(f"  /              → latest digest")
    print(f"  /neighborhoods → NYC neighborhood ranker")
    print(f"  /nyc           → The Jawnz Diagnostic")
    server.serve_forever()
