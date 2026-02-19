"""Tiny server that serves the latest Shooter Digest HTML."""

import os
import glob
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


class DigestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def end_headers(self):
        # Prevent aggressive caching so new deploys are seen immediately
        self.send_header("Cache-Control", "no-cache, max-age=0")
        super().end_headers()

    def do_GET(self):
        # Serve the latest digest HTML at /
        if self.path == "/" or self.path == "/index.html":
            files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html")))
            if files:
                self.path = "/" + os.path.basename(files[-1])
        super().do_GET()


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DigestHandler)
    print(f"Serving Shooter Digest on port {PORT}")
    server.serve_forever()
